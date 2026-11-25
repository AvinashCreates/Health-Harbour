package main

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"regexp"
	"time"
)

var (
	eventIDPattern     = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`)
	digestPattern      = regexp.MustCompile(`^[0-9a-f]{64}$`)
	eventTypePattern   = regexp.MustCompile(`^[A-Za-z][A-Za-z0-9._:-]{0,63}$`)
	referencePattern   = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$`)
	resourceTypePattern = regexp.MustCompile(`^[A-Z][A-Za-z0-9]{0,63}$`)
)

var errIdempotencyConflict = errors.New("eventId already exists with different content")

func convertOutboxEvent(outbox OutboxEvent) (ClinicalEvent, error) {
	if !eventIDPattern.MatchString(outbox.EventID) {
		return ClinicalEvent{}, fmt.Errorf("invalid eventId")
	}
	if !eventTypePattern.MatchString(outbox.EventType) {
		return ClinicalEvent{}, fmt.Errorf("invalid eventType")
	}
	if !referencePattern.MatchString(outbox.ActorRef) {
		return ClinicalEvent{}, fmt.Errorf("invalid actorRef")
	}
	if !digestPattern.MatchString(outbox.PayloadHash) {
		return ClinicalEvent{}, fmt.Errorf("invalid payloadHash")
	}
	if len(outbox.OccurredAt) == 0 || outbox.OccurredAt[len(outbox.OccurredAt)-1] != 'Z' {
		return ClinicalEvent{}, fmt.Errorf("occurredAt must be UTC RFC3339")
	}
	occurredAt, err := time.Parse(time.RFC3339Nano, outbox.OccurredAt)
	if err != nil || occurredAt.UTC().Format(time.RFC3339Nano) != outbox.OccurredAt {
		return ClinicalEvent{}, fmt.Errorf("occurredAt must be canonical UTC RFC3339")
	}
	if outbox.ResourceType != nil && !resourceTypePattern.MatchString(*outbox.ResourceType) {
		return ClinicalEvent{}, fmt.Errorf("invalid resourceType")
	}
	subjectHash, err := hashNullableReference(outbox.SubjectRef)
	if err != nil {
		return ClinicalEvent{}, fmt.Errorf("invalid subjectRef")
	}
	resourceHash, err := hashNullableReference(outbox.ResourceRef)
	if err != nil {
		return ClinicalEvent{}, fmt.Errorf("invalid resourceRef")
	}
	actorDigest := sha256.Sum256([]byte(outbox.ActorRef))
	return ClinicalEvent{
		EventID:         outbox.EventID,
		EventType:       outbox.EventType,
		ActorRefHash:    hex.EncodeToString(actorDigest[:]),
		SubjectRefHash:  subjectHash,
		ResourceRefHash: resourceHash,
		ResourceType:    outbox.ResourceType,
		OccurredAt:      outbox.OccurredAt,
		PayloadHash:     outbox.PayloadHash,
	}, nil
}

func hashNullableReference(reference *string) (*string, error) {
	if reference == nil {
		return nil, nil
	}
	if !referencePattern.MatchString(*reference) {
		return nil, fmt.Errorf("invalid reference")
	}
	digest := sha256.Sum256([]byte(*reference))
	hashed := hex.EncodeToString(digest[:])
	return &hashed, nil
}

func validateClinicalEvent(event ClinicalEvent) error {
	if !eventIDPattern.MatchString(event.EventID) ||
		!eventTypePattern.MatchString(event.EventType) ||
		!digestPattern.MatchString(event.ActorRefHash) ||
		!digestPattern.MatchString(event.PayloadHash) {
		return fmt.Errorf("invalid event identifiers")
	}
	if event.SubjectRefHash != nil && !digestPattern.MatchString(*event.SubjectRefHash) {
		return fmt.Errorf("invalid subject reference digest")
	}
	if event.ResourceRefHash != nil && !digestPattern.MatchString(*event.ResourceRefHash) {
		return fmt.Errorf("invalid resource reference digest")
	}
	if event.ResourceType != nil && !resourceTypePattern.MatchString(*event.ResourceType) {
		return fmt.Errorf("invalid resource type")
	}
	timestamp, err := time.Parse(time.RFC3339Nano, event.OccurredAt)
	if err != nil || timestamp.UTC().Format(time.RFC3339Nano) != event.OccurredAt {
		return fmt.Errorf("invalid timestamp")
	}
	return nil
}
