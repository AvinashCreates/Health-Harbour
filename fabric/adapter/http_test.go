package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

const testToken = "test-token-with-at-least-thirty-two-characters"

func hashReference(reference string) string {
	digest := sha256.Sum256([]byte(reference))
	return hex.EncodeToString(digest[:])
}

type fakeSubmitter struct {
	called       bool
	receivedBody []byte
	transactionID string
}

func (f *fakeSubmitter) SubmitEvent(_ context.Context, _ string, payload []byte) (string, error) {
	f.called = true
	f.receivedBody = append([]byte(nil), payload...)
	if f.transactionID == "" {
		f.transactionID = "fabric-tx-123"
	}
	return f.transactionID, nil
}

func testAPI() (*httpAPI, *fakeSubmitter) {
	fake := &fakeSubmitter{}
	return &httpAPI{
		submitter: fake,
		tokenHash: sha256.Sum256([]byte(testToken)),
	}, fake
}

func TestCreateEventRequiresBearerAuthentication(t *testing.T) {
	api, fake := testAPI()
	handler := api.authenticated(http.HandlerFunc(api.createEvent))
	request := httptest.NewRequest(http.MethodPost, "/events", strings.NewReader(validEventJSON))
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)
	if response.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", response.Code, http.StatusUnauthorized)
	}
	if fake.called {
		t.Fatal("unauthenticated request reached submitter")
	}
}

func TestCreateEventReturnsOnlyAfterCommit(t *testing.T) {
	api, fake := testAPI()
	handler := api.authenticated(http.HandlerFunc(api.createEvent))
	request := httptest.NewRequest(http.MethodPost, "/events", strings.NewReader(validEventJSON))
	request.Header.Set("Authorization", "Bearer "+testToken)
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)
	if response.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d; body=%s", response.Code, http.StatusOK, response.Body)
	}
	if !fake.called {
		t.Fatal("valid event was not submitted")
	}
	if response.Body.String() != "{\"transactionId\":\"fabric-tx-123\"}\n" {
		t.Fatalf("unexpected success response: %s", response.Body)
	}
	for _, rawReference := range []string{"patient-123", "clinician-456", "resource-789"} {
		if strings.Contains(string(fake.receivedBody), rawReference) {
			t.Fatalf("raw references were sent to Fabric: %s", fake.receivedBody)
		}
	}
	var ledgerEvent ClinicalEvent
	if err := json.Unmarshal(fake.receivedBody, &ledgerEvent); err != nil {
		t.Fatalf("decode ledger event: %v", err)
	}
	if ledgerEvent.ActorRefHash != hashReference("clinician-456") {
		t.Fatalf("actorRef was not hashed: %s", ledgerEvent.ActorRefHash)
	}
	if ledgerEvent.SubjectRefHash == nil || *ledgerEvent.SubjectRefHash != hashReference("patient-123") {
		t.Fatalf("subjectRef was not hashed: %#v", ledgerEvent.SubjectRefHash)
	}
	if ledgerEvent.ResourceRefHash == nil || *ledgerEvent.ResourceRefHash != hashReference("resource-789") {
		t.Fatalf("resourceRef was not hashed: %#v", ledgerEvent.ResourceRefHash)
	}
}

func TestCreateEventRejectsPHIAndUnknownFields(t *testing.T) {
	api, fake := testAPI()
	handler := api.authenticated(http.HandlerFunc(api.createEvent))
	body := strings.TrimSuffix(strings.TrimSpace(validEventJSON), "}") + `,"patientName":"Jane Doe"}`
	request := httptest.NewRequest(http.MethodPost, "/events", strings.NewReader(body))
	request.Header.Set("Authorization", "Bearer "+testToken)
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)
	if response.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want %d", response.Code, http.StatusBadRequest)
	}
	if fake.called {
		t.Fatal("invalid event reached submitter")
	}
}

func TestCreateEventAcceptsNullableReferencesAndResourceType(t *testing.T) {
	api, fake := testAPI()
	handler := api.authenticated(http.HandlerFunc(api.createEvent))
	body := strings.ReplaceAll(validEventJSON, `"patient-123"`, `null`)
	body = strings.ReplaceAll(body, `"resource-789"`, `null`)
	body = strings.ReplaceAll(body, `"Observation"`, `null`)
	request := httptest.NewRequest(http.MethodPost, "/events", strings.NewReader(body))
	request.Header.Set("Authorization", "Bearer "+testToken)
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)
	if response.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d; body=%s", response.Code, http.StatusOK, response.Body)
	}
	var ledgerEvent ClinicalEvent
	if err := json.Unmarshal(fake.receivedBody, &ledgerEvent); err != nil {
		t.Fatalf("decode ledger event: %v", err)
	}
	if ledgerEvent.SubjectRefHash != nil || ledgerEvent.ResourceRefHash != nil || ledgerEvent.ResourceType != nil {
		t.Fatalf("nullable fields should remain null: %+v", ledgerEvent)
	}
}

func TestConvertOutboxEventAcceptsBackendEventTypes(t *testing.T) {
	eventTypes := []string{
		"CONSENT_GRANTED",
		"CONSENT_REVOKED",
		"SERVICE_REQUEST_CREATED",
		"DIAGNOSTIC_REPORT_FINALIZED",
		"CLINICAL_REVIEW_RECORDED",
		"DATA_ACCESSED",
		"SPECIMEN_REGISTERED",
	}
	for _, eventType := range eventTypes {
		t.Run(eventType, func(t *testing.T) {
			outbox := OutboxEvent{
				EventID:     "550e8400-e29b-41d4-a716-446655440000",
				EventType:   eventType,
				ActorRef:    "actor-001",
				OccurredAt:  "2026-01-02T03:04:05Z",
				PayloadHash: strings.Repeat("a", 64),
			}
			event, err := convertOutboxEvent(outbox)
			if err != nil {
				t.Fatalf("convert %s: %v", eventType, err)
			}
			if event.EventType != eventType {
				t.Fatalf("eventType = %q, want %q", event.EventType, eventType)
			}
		})
	}
}

func TestConvertOutboxEventPreservesNullableFieldsAsNull(t *testing.T) {
	event, err := convertOutboxEvent(OutboxEvent{
		EventID:     "550e8400-e29b-41d4-a716-446655440000",
		EventType:   "DATA_ACCESSED",
		ActorRef:    "actor-001",
		SubjectRef:  nil,
		ResourceRef: nil,
		ResourceType: nil,
		OccurredAt:  "2026-01-02T03:04:05Z",
		PayloadHash: strings.Repeat("a", 64),
	})
	if err != nil {
		t.Fatalf("convert event with nullable references: %v", err)
	}
	payload, err := json.Marshal(event)
	if err != nil {
		t.Fatalf("marshal ledger event: %v", err)
	}
	for _, field := range []string{`"subjectRefHash":null`, `"resourceRefHash":null`, `"resourceType":null`} {
		if !strings.Contains(string(payload), field) {
			t.Errorf("ledger event missing nullable field %s: %s", field, payload)
		}
	}
}

func TestFabricSubmitterRetriesReturnPriorCommittedTransaction(t *testing.T) {
	records := map[string]*storedEvent{}
	submits := 0
	submitter := &fabricSubmitter{
		lookup: func(_ context.Context, eventID string) (*storedEvent, error) {
			return records[eventID], nil
		},
		submit: func(_ context.Context, payload []byte) (string, error) {
			submits++
			digest := sha256.Sum256(payload)
			records["550e8400-e29b-41d4-a716-446655440000"] = &storedEvent{
				TransactionID: "original-fabric-tx",
				EventDigest:   hex.EncodeToString(digest[:]),
			}
			return "original-fabric-tx", nil
		},
	}
	eventID := "550e8400-e29b-41d4-a716-446655440000"
	payload := []byte(`{"eventId":"550e8400-e29b-41d4-a716-446655440000"}`)
	first, err := submitter.SubmitEvent(context.Background(), eventID, payload)
	if err != nil {
		t.Fatalf("first submit: %v", err)
	}
	retry, err := submitter.SubmitEvent(context.Background(), eventID, payload)
	if err != nil {
		t.Fatalf("retry: %v", err)
	}
	if first != "original-fabric-tx" || retry != first {
		t.Fatalf("transaction IDs first=%q retry=%q", first, retry)
	}
	if submits != 1 {
		t.Fatalf("submit count = %d, want 1", submits)
	}
	if _, err := submitter.SubmitEvent(context.Background(), eventID, []byte(`{"different":"content"}`)); err != errIdempotencyConflict {
		t.Fatalf("different content error = %v, want idempotency conflict", err)
	}
}

func TestFabricSubmitterResolvesConcurrentCommitAfterSubmitError(t *testing.T) {
	records := map[string]*storedEvent{}
	eventID := "550e8400-e29b-41d4-a716-446655440000"
	payload := []byte(`{"eventId":"550e8400-e29b-41d4-a716-446655440000"}`)
	submitter := &fabricSubmitter{
		lookup: func(_ context.Context, id string) (*storedEvent, error) {
			return records[id], nil
		},
		submit: func(_ context.Context, body []byte) (string, error) {
			digest := sha256.Sum256(body)
			records[eventID] = &storedEvent{
				TransactionID: "concurrent-committed-tx",
				EventDigest:   hex.EncodeToString(digest[:]),
			}
			return "", errors.New("duplicate transaction lost validation race")
		},
	}
	transactionID, err := submitter.SubmitEvent(context.Background(), eventID, payload)
	if err != nil {
		t.Fatalf("concurrent retry was not resolved: %v", err)
	}
	if transactionID != "concurrent-committed-tx" {
		t.Fatalf("transaction ID = %q, want the prior commit ID", transactionID)
	}
}

const validEventJSON = `{
  "eventId":"550e8400-e29b-41d4-a716-446655440000",
  "eventType":"clinical.resource.created",
  "actorRef":"clinician-456",
  "subjectRef":"patient-123",
  "resourceRef":"resource-789",
  "resourceType":"Observation",
  "occurredAt":"2026-01-02T03:04:05Z",
  "payloadHash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}`
