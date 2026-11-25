package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"regexp"
	"strings"
	"time"

	"github.com/hyperledger/fabric-chaincode-go/shim"
	peer "github.com/hyperledger/fabric-protos-go/peer"
)

const maxEventSize = 4096

var (
	uuidPattern         = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`)
	hashPattern         = regexp.MustCompile(`^[0-9a-f]{64}$`)
	resourceTypePattern = regexp.MustCompile(`^[A-Z][A-Za-z0-9]{0,63}$`)
)

var allowedEventTypes = map[string]struct{}{
	"CONSENT_GRANTED":             {},
	"CONSENT_REVOKED":             {},
	"SERVICE_REQUEST_CREATED":     {},
	"SPECIMEN_REGISTERED":         {},
	"DIAGNOSTIC_REPORT_FINALIZED": {},
	"CLINICAL_REVIEW_RECORDED":    {},
	"LAB_REPORT_FINALIZED":        {},
	"PHYSICIAN_REVIEW_RECORDED":   {},
	"DATA_ACCESSED":               {},
	"DOCUMENT_UPLOADED":           {},
	"DOCUMENT_DELETED":            {},
}

// ClinicalEventInput is the ledger-safe projection of a backend outbox event.
type ClinicalEventInput struct {
	EventID         string  `json:"eventId"`
	EventType       string  `json:"eventType"`
	ActorRefHash    string  `json:"actorRefHash"`
	SubjectRefHash  *string `json:"subjectRefHash"`
	ResourceRefHash *string `json:"resourceRefHash"`
	ResourceType    *string `json:"resourceType"`
	OccurredAt      string  `json:"occurredAt"`
	PayloadHash     string  `json:"payloadHash"`
}

type ClinicalEvent struct {
	EventID         string  `json:"eventId"`
	EventType       string  `json:"eventType"`
	ActorRefHash    string  `json:"actorRefHash"`
	LedgerActorHash string  `json:"ledgerActorHash"`
	SubjectRefHash  *string `json:"subjectRefHash"`
	ResourceRefHash *string `json:"resourceRefHash"`
	ResourceType    *string `json:"resourceType"`
	OccurredAt      string  `json:"occurredAt"`
	PayloadHash     string  `json:"payloadHash"`
	EventDigest     string  `json:"eventDigest"`
	TransactionID   string  `json:"transactionId"`
}

type ProvenanceChaincode struct{}

func (c *ProvenanceChaincode) Init(shim.ChaincodeStubInterface) peer.Response {
	return shim.Success(nil)
}

func (c *ProvenanceChaincode) Invoke(stub shim.ChaincodeStubInterface) peer.Response {
	function, args := stub.GetFunctionAndParameters()
	switch function {
	case "RecordEvent":
		if len(args) != 1 {
			return shim.Error("RecordEvent requires one JSON event argument")
		}
		result, err := recordEvent(stub, []byte(args[0]))
		if err != nil {
			return shim.Error(err.Error())
		}
		return shim.Success(result)
	case "ReadEvent":
		if len(args) != 1 {
			return shim.Error("ReadEvent requires one eventId argument")
		}
		result, err := readEvent(stub, args[0])
		if err != nil {
			return shim.Error(err.Error())
		}
		return shim.Success(result)
	case "GetEvent":
		if len(args) != 1 {
			return shim.Error("GetEvent requires one eventId argument")
		}
		result, err := getEvent(stub, args[0])
		if err != nil {
			return shim.Error(err.Error())
		}
		return shim.Success(result)
	default:
		return shim.Error("unsupported transaction")
	}
}

func recordEvent(stub shim.ChaincodeStubInterface, payload []byte) ([]byte, error) {
	input, canonicalInput, err := parseClinicalEvent(payload)
	if err != nil {
		return nil, err
	}
	creator, err := stub.GetCreator()
	if err != nil || len(creator) == 0 {
		return nil, fmt.Errorf("transaction creator identity is unavailable")
	}
	actorDigest := sha256.Sum256(creator)
	eventDigest := sha256.Sum256(canonicalInput)
	event := ClinicalEvent{
		EventID:         input.EventID,
		EventType:       input.EventType,
		ActorRefHash:    input.ActorRefHash,
		LedgerActorHash: hex.EncodeToString(actorDigest[:]),
		SubjectRefHash:  input.SubjectRefHash,
		ResourceRefHash: input.ResourceRefHash,
		ResourceType:    input.ResourceType,
		OccurredAt:      input.OccurredAt,
		PayloadHash:     input.PayloadHash,
		EventDigest:     hex.EncodeToString(eventDigest[:]),
		TransactionID:   stub.GetTxID(),
	}
	canonicalJSON, err := json.Marshal(event)
	if err != nil {
		return nil, fmt.Errorf("encode event")
	}

	key, err := stub.CreateCompositeKey("clinical-event", []string{event.EventID})
	if err != nil {
		return nil, fmt.Errorf("create event key: %w", err)
	}
	existing, err := stub.GetState(key)
	if err != nil {
		return nil, fmt.Errorf("read event: %w", err)
	}
	if existing != nil {
		return nil, fmt.Errorf("event already exists")
	}
	if err := stub.PutState(key, canonicalJSON); err != nil {
		return nil, fmt.Errorf("store event: %w", err)
	}
	if err := stub.SetEvent("ClinicalProvenanceRecorded", canonicalJSON); err != nil {
		return nil, fmt.Errorf("emit provenance event: %w", err)
	}
	return canonicalJSON, nil
}

func readEvent(stub shim.ChaincodeStubInterface, eventID string) ([]byte, error) {
	value, err := getEvent(stub, eventID)
	if err != nil {
		return nil, err
	}
	if value == nil {
		return nil, fmt.Errorf("event not found")
	}
	return value, nil
}

func getEvent(stub shim.ChaincodeStubInterface, eventID string) ([]byte, error) {
	if !uuidPattern.MatchString(eventID) {
		return nil, fmt.Errorf("invalid eventId")
	}
	key, err := stub.CreateCompositeKey("clinical-event", []string{eventID})
	if err != nil {
		return nil, fmt.Errorf("create event key: %w", err)
	}
	value, err := stub.GetState(key)
	if err != nil {
		return nil, fmt.Errorf("read event: %w", err)
	}
	return value, nil
}

func parseClinicalEvent(payload []byte) (*ClinicalEventInput, []byte, error) {
	if len(payload) == 0 || len(payload) > maxEventSize {
		return nil, nil, fmt.Errorf("event payload must be between 1 and %d bytes", maxEventSize)
	}

	decoder := json.NewDecoder(bytes.NewReader(payload))
	decoder.DisallowUnknownFields()
	var event ClinicalEventInput
	if err := decoder.Decode(&event); err != nil {
		return nil, nil, fmt.Errorf("invalid event JSON")
	}
	var trailing any
	if err := decoder.Decode(&trailing); err != io.EOF {
		return nil, nil, fmt.Errorf("event must contain exactly one JSON object")
	}

	if !uuidPattern.MatchString(event.EventID) {
		return nil, nil, fmt.Errorf("eventId must be a canonical lowercase UUID")
	}
	if !isAllowedEventType(event.EventType) {
		return nil, nil, fmt.Errorf("unsupported eventType")
	}
	if !hashPattern.MatchString(event.ActorRefHash) || !hashPattern.MatchString(event.PayloadHash) {
		return nil, nil, fmt.Errorf("actorRefHash and payloadHash must be lowercase SHA-256 digests")
	}
	for name, value := range map[string]*string{
		"subjectRefHash":  event.SubjectRefHash,
		"resourceRefHash": event.ResourceRefHash,
	} {
		if value != nil && !hashPattern.MatchString(*value) {
			return nil, nil, fmt.Errorf("%s must be a lowercase SHA-256 digest", name)
		}
		if value != nil {
			if _, err := hex.DecodeString(*value); err != nil {
				return nil, nil, fmt.Errorf("%s must be a lowercase SHA-256 digest", name)
			}
		}
	}
	if event.ResourceType != nil && !resourceTypePattern.MatchString(*event.ResourceType) {
		return nil, nil, fmt.Errorf("invalid resourceType")
	}
	if !strings.HasSuffix(event.OccurredAt, "Z") {
		return nil, nil, fmt.Errorf("occurredAt must be UTC RFC3339")
	}
	occurredAt, err := time.Parse(time.RFC3339Nano, event.OccurredAt)
	if err != nil || occurredAt.UTC().Format(time.RFC3339Nano) != event.OccurredAt {
		return nil, nil, fmt.Errorf("occurredAt must be UTC RFC3339")
	}

	canonicalJSON, err := json.Marshal(event)
	if err != nil {
		return nil, nil, fmt.Errorf("encode event")
	}
	return &event, canonicalJSON, nil
}

func isAllowedEventType(eventType string) bool {
	_, allowed := allowedEventTypes[eventType]
	return allowed
}
