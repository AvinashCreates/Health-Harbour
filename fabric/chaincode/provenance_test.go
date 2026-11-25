package main

import (
	"strings"
	"testing"

	"github.com/hyperledger/fabric-chaincode-go/shim"
	"github.com/hyperledger/fabric-chaincode-go/shimtest"
	peer "github.com/hyperledger/fabric-protos-go/peer"
)

const validEvent = `{
  "eventId":"550e8400-e29b-41d4-a716-446655440000",
  "eventType":"SERVICE_REQUEST_CREATED",
  "actorRefHash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "subjectRefHash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "resourceRefHash":null,
  "resourceType":"Observation",
  "occurredAt":"2026-01-02T03:04:05Z",
  "payloadHash":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
}`

func TestParseClinicalEventAcceptsValidProvenance(t *testing.T) {
	event, canonical, err := parseClinicalEvent([]byte(validEvent))
	if err != nil {
		t.Fatalf("parse valid event: %v", err)
	}
	if event.EventID != "550e8400-e29b-41d4-a716-446655440000" {
		t.Fatalf("unexpected event ID: %q", event.EventID)
	}
	if !strings.Contains(string(canonical), `"resourceType":"Observation"`) {
		t.Fatalf("canonical JSON missing resource type: %s", canonical)
	}
}

func TestParseClinicalEventAcceptsBackendEventTypes(t *testing.T) {
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
			payload := strings.Replace(validEvent, "SERVICE_REQUEST_CREATED", eventType, 1)
			event, _, err := parseClinicalEvent([]byte(payload))
			if err != nil {
				t.Fatalf("parse event type %s: %v", eventType, err)
			}
			if event.EventType != eventType {
				t.Fatalf("eventType = %q, want %q", event.EventType, eventType)
			}
		})
	}
}

func TestParseClinicalEventRejectsUnapprovedEventType(t *testing.T) {
	payload := strings.Replace(validEvent, "SERVICE_REQUEST_CREATED", "UNREVIEWED_EVENT", 1)
	if _, _, err := parseClinicalEvent([]byte(payload)); err == nil {
		t.Fatal("unapproved event type was accepted")
	}
}

func TestParseClinicalEventAcceptsAllNullableBackendFields(t *testing.T) {
	payload := strings.Replace(validEvent, `"subjectRefHash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"`, `"subjectRefHash":null`, 1)
	payload = strings.Replace(payload, `"resourceType":"Observation"`, `"resourceType":null`, 1)
	event, _, err := parseClinicalEvent([]byte(payload))
	if err != nil {
		t.Fatalf("parse event with nullable backend fields: %v", err)
	}
	if event.SubjectRefHash != nil || event.ResourceRefHash != nil || event.ResourceType != nil {
		t.Fatalf("nullable fields did not remain null: %+v", event)
	}
}

func TestParseClinicalEventRejectsUnknownAndFreeTextFields(t *testing.T) {
	payload := strings.TrimSuffix(strings.TrimSpace(validEvent), "}") + `,"patientName":"Jane Doe"}`
	if _, _, err := parseClinicalEvent([]byte(payload)); err == nil {
		t.Fatal("expected free-text/unknown field to be rejected")
	}
}

func TestParseClinicalEventRejectsInvalidReferencesAndEnums(t *testing.T) {
	tests := []struct {
		name string
		old  string
		new  string
	}{
		{"raw subject reference", `"subjectRefHash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"`, `"subjectRefHash":"patient-123"`},
		{"invalid payload hash", `"payloadHash":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"`, `"payloadHash":"not-a-digest"`},
		{"invalid event type", `"eventType":"SERVICE_REQUEST_CREATED"`, `"eventType":"free text"`},
		{"non-UTC time", `"occurredAt":"2026-01-02T03:04:05Z"`, `"occurredAt":"2026-01-02T03:04:05+01:00"`},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			payload := strings.Replace(validEvent, test.old, test.new, 1)
			if _, _, err := parseClinicalEvent([]byte(payload)); err == nil {
				t.Fatal("expected validation failure")
			}
		})
	}
}

func TestParseClinicalEventRejectsOversizeAndTrailingJSON(t *testing.T) {
	if _, _, err := parseClinicalEvent([]byte(strings.Repeat(" ", maxEventSize+1))); err == nil {
		t.Fatal("expected oversized payload to be rejected")
	}
	if _, _, err := parseClinicalEvent([]byte(validEvent + ` {}`)); err == nil {
		t.Fatal("expected trailing JSON to be rejected")
	}
}

func TestRecordEventIsAppendOnlyAndReadable(t *testing.T) {
	stub := shimtest.NewMockStub("clinical-provenance", new(ProvenanceChaincode))
	record := [][]byte{[]byte("RecordEvent"), []byte(validEvent)}
	missing := stub.MockInvoke("tx-get-missing", [][]byte{
		[]byte("GetEvent"),
		[]byte("550e8400-e29b-41d4-a716-446655440000"),
	})
	if missing.Status != 200 || len(missing.Payload) != 0 {
		t.Fatalf("missing GetEvent should return an empty success: %#v", missing)
	}

	response := invokeWithCreator(stub, "tx-record-1", record)
	if response.Status != 200 {
		t.Fatalf("record status = %d, want 200: %s", response.Status, response.Message)
	}

	duplicate := invokeWithCreator(stub, "tx-record-2", record)
	if duplicate.Status == 200 {
		t.Fatal("duplicate event ID was accepted")
	}

	read := stub.MockInvoke("tx-read", [][]byte{
		[]byte("ReadEvent"),
		[]byte("550e8400-e29b-41d4-a716-446655440000"),
	})
	if read.Status != 200 {
		t.Fatalf("read status = %d, want 200: %s", read.Status, read.Message)
	}
	if !strings.Contains(string(read.Payload), `"eventId":"550e8400-e29b-41d4-a716-446655440000"`) {
		t.Fatalf("read payload missing event: %s", read.Payload)
	}
	if !strings.Contains(string(read.Payload), `"actorRefHash":"`) {
		t.Fatalf("stored event missing derived actor reference: %s", read.Payload)
	}
	if !strings.Contains(string(read.Payload), `"transactionId":"tx-record-1"`) {
		t.Fatalf("stored event missing original transaction ID: %s", read.Payload)
	}
	if !strings.Contains(string(read.Payload), `"eventType":"SERVICE_REQUEST_CREATED"`) {
		t.Fatalf("stored event missing eventType: %s", read.Payload)
	}
	if !strings.Contains(string(read.Payload), `"subjectRefHash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"`) {
		t.Fatalf("stored event missing subject digest: %s", read.Payload)
	}
	found := stub.MockInvoke("tx-get-found", [][]byte{
		[]byte("GetEvent"),
		[]byte("550e8400-e29b-41d4-a716-446655440000"),
	})
	if found.Status != 200 || !strings.Contains(string(found.Payload), `"transactionId":"tx-record-1"`) {
		t.Fatalf("GetEvent failed to expose committed idempotency record: %#v", found)
	}
}

type creatorStub struct {
	shim.ChaincodeStubInterface
}

func (creatorStub) GetCreator() ([]byte, error) {
	return []byte("Org1MSP:User1"), nil
}

func invokeWithCreator(stub *shimtest.MockStub, txID string, args [][]byte) peer.Response {
	stub.Creator = []byte("Org1MSP:User1")
	return stub.MockInvoke(txID, args)
}
