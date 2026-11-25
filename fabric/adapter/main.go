package main

import (
	"context"
	"crypto/sha256"
	"crypto/subtle"
	"crypto/x509"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/hyperledger/fabric-gateway/pkg/client"
	"github.com/hyperledger/fabric-gateway/pkg/identity"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
)

const maxRequestBytes = 4096

type OutboxEvent struct {
	EventID      string  `json:"eventId"`
	EventType    string  `json:"eventType"`
	ActorRef     string  `json:"actorRef"`
	SubjectRef   *string `json:"subjectRef"`
	ResourceRef  *string `json:"resourceRef"`
	ResourceType *string `json:"resourceType"`
	OccurredAt   string  `json:"occurredAt"`
	PayloadHash  string  `json:"payloadHash"`
}

type ClinicalEvent struct {
	EventID         string  `json:"eventId"`
	EventType       string  `json:"eventType"`
	ActorRefHash    string  `json:"actorRefHash"`
	SubjectRefHash  *string `json:"subjectRefHash"`
	ResourceRefHash *string `json:"resourceRefHash"`
	ResourceType    *string `json:"resourceType"`
	OccurredAt      string  `json:"occurredAt"`
	PayloadHash     string  `json:"payloadHash"`
}

type submitter interface {
	SubmitEvent(context.Context, string, []byte) (string, error)
}

type storedEvent struct {
	TransactionID string `json:"transactionId"`
	EventDigest   string `json:"eventDigest"`
}

type fabricSubmitter struct {
	lookup func(context.Context, string) (*storedEvent, error)
	submit func(context.Context, []byte) (string, error)
}

func (s *fabricSubmitter) SubmitEvent(ctx context.Context, eventID string, payload []byte) (string, error) {
	digest := sha256.Sum256(payload)
	digestHex := hex.EncodeToString(digest[:])
	existing, err := s.lookup(ctx, eventID)
	if err != nil {
		return "", err
	}
	if existing != nil {
		if existing.EventDigest != digestHex {
			return "", errIdempotencyConflict
		}
		return existing.TransactionID, nil
	}

	transactionID, submitErr := s.submit(ctx, payload)
	if submitErr == nil {
		return transactionID, nil
	}

	// A concurrent retry may have committed the same event while this
	// transaction was being endorsed or ordered. Resolve that race by reading
	// the committed record and returning its original transaction ID.
	existing, lookupErr := s.lookup(ctx, eventID)
	if lookupErr == nil && existing != nil {
		if existing.EventDigest != digestHex {
			return "", errIdempotencyConflict
		}
		return existing.TransactionID, nil
	}
	return "", submitErr
}

type httpAPI struct {
	submitter submitter
	tokenHash [32]byte
}

func main() {
	token := os.Getenv("FABRIC_GATEWAY_TOKEN")
	if len(token) < 32 {
		log.Fatal("FABRIC_GATEWAY_TOKEN must be at least 32 characters")
	}
	gateway, connection, err := connectGateway()
	if err != nil {
		log.Fatalf("connect to Fabric Gateway: %v", err)
	}
	defer connection.Close()
	defer gateway.Close()

	channelName := envOr("CHANNEL_NAME", "mychannel")
	chaincodeName := envOr("CHAINCODE_NAME", "clinical-provenance")
	contract := gateway.GetNetwork(channelName).GetContract(chaincodeName)
	api := &httpAPI{
		submitter: &fabricSubmitter{
			lookup: func(ctx context.Context, eventID string) (*storedEvent, error) {
				result, err := contract.EvaluateWithContext(
					ctx, "GetEvent", client.WithArguments(eventID),
				)
				if err != nil {
					return nil, err
				}
				if len(result) == 0 {
					return nil, nil
				}
				var record storedEvent
				if err := json.Unmarshal(result, &record); err != nil {
					return nil, fmt.Errorf("decode committed event: %w", err)
				}
				if record.TransactionID == "" || record.EventDigest == "" {
					return nil, fmt.Errorf("committed event is missing idempotency metadata")
				}
				return &record, nil
			},
			submit: func(ctx context.Context, payload []byte) (string, error) {
				_, commit, err := contract.SubmitAsyncWithContext(
					ctx, "RecordEvent", client.WithArguments(string(payload)),
				)
				if err != nil {
					return "", err
				}
				status, err := commit.Status()
				if err != nil {
					return "", err
				}
				if !status.Successful {
					return "", fmt.Errorf("transaction %s failed validation with code %d", status.TransactionID, int32(status.Code))
				}
				return status.TransactionID, nil
			},
		},
		tokenHash: sha256.Sum256([]byte(token)),
	}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	})
	mux.Handle("POST /events", api.authenticated(http.HandlerFunc(api.createEvent)))

	server := &http.Server{
		Addr:              envOr("LISTEN_ADDR", "127.0.0.1:8080"),
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      45 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
	log.Printf("Fabric provenance adapter listening on %s", server.Addr)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatalf("serve HTTP: %v", err)
	}
}

func (api *httpAPI) authenticated(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		const prefix = "Bearer "
		header := r.Header.Get("Authorization")
		if !strings.HasPrefix(header, prefix) || len(header) == len(prefix) {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		candidate := sha256.Sum256([]byte(strings.TrimPrefix(header, prefix)))
		if subtle.ConstantTimeCompare(candidate[:], api.tokenHash[:]) != 1 {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func (api *httpAPI) createEvent(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, maxRequestBytes)
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	var outboxEvent OutboxEvent
	if err := decoder.Decode(&outboxEvent); err != nil {
		http.Error(w, "invalid event payload", http.StatusBadRequest)
		return
	}
	var trailing any
	if err := decoder.Decode(&trailing); err != io.EOF {
		http.Error(w, "invalid event payload", http.StatusBadRequest)
		return
	}
	event, err := convertOutboxEvent(outboxEvent)
	if err != nil {
		http.Error(w, "invalid event payload", http.StatusBadRequest)
		return
	}
	payload, err := json.Marshal(event)
	if err != nil || validateClinicalEvent(event) != nil {
		http.Error(w, "invalid event payload", http.StatusBadRequest)
		return
	}
	transactionID, err := api.submitter.SubmitEvent(r.Context(), event.EventID, payload)
	if err != nil {
		if errors.Is(err, errIdempotencyConflict) {
			http.Error(w, "eventId already exists with different content", http.StatusConflict)
			return
		}
		http.Error(w, "Fabric transaction failed or was not confirmed", http.StatusBadGateway)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]string{"transactionId": transactionID})
}

func connectGateway() (*client.Gateway, *grpc.ClientConn, error) {
	certPEM, err := os.ReadFile(requiredEnv("CERT_PATH"))
	if err != nil {
		return nil, nil, fmt.Errorf("read client certificate: %w", err)
	}
	certificate, err := identityCertificate(certPEM)
	if err != nil {
		return nil, nil, err
	}
	privateKeyPEM, err := os.ReadFile(requiredEnv("KEY_PATH"))
	if err != nil {
		return nil, nil, fmt.Errorf("read client signing key: %w", err)
	}
	privateKey, err := identity.PrivateKeyFromPEM(privateKeyPEM)
	if err != nil {
		return nil, nil, fmt.Errorf("parse client signing key: %w", err)
	}
	id, err := identity.NewX509Identity(requiredEnv("MSP_ID"), certificate)
	if err != nil {
		return nil, nil, fmt.Errorf("create client identity: %w", err)
	}
	sign, err := identity.NewPrivateKeySign(privateKey)
	if err != nil {
		return nil, nil, fmt.Errorf("create signing function: %w", err)
	}
	tlsCertPath := requiredEnv("TLS_CERT_PATH")
	tlsServerName := requiredEnv("TLS_SERVER_NAME")
	transportCredentials, err := credentials.NewClientTLSFromFile(tlsCertPath, tlsServerName)
	if err != nil {
		return nil, nil, fmt.Errorf("load peer TLS certificate: %w", err)
	}
	connection, err := grpc.NewClient(
		requiredEnv("PEER_ENDPOINT"),
		grpc.WithTransportCredentials(transportCredentials),
	)
	if err != nil {
		return nil, nil, fmt.Errorf("create peer connection: %w", err)
	}
	gateway, err := client.Connect(
		id,
		client.WithSign(sign),
		client.WithClientConnection(connection),
		client.WithEvaluateTimeout(10*time.Second),
		client.WithEndorseTimeout(30*time.Second),
		client.WithSubmitTimeout(30*time.Second),
		client.WithCommitStatusTimeout(35*time.Second),
	)
	if err != nil {
		_ = connection.Close()
		return nil, nil, fmt.Errorf("connect Fabric Gateway: %w", err)
	}
	return gateway, connection, nil
}

func identityCertificate(pemBytes []byte) (*x509.Certificate, error) {
	certificate, err := identity.CertificateFromPEM(pemBytes)
	if err != nil {
		return nil, fmt.Errorf("parse client certificate: %w", err)
	}
	return certificate, nil
}

func requiredEnv(name string) string {
	value := strings.TrimSpace(os.Getenv(name))
	if value == "" {
		log.Fatalf("%s is required", name)
	}
	return value
}

func envOr(name, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(name)); value != "" {
		return value
	}
	return fallback
}
