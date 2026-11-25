package main

import (
	"log"

	"github.com/hyperledger/fabric-chaincode-go/shim"
)

func main() {
	if err := shim.Start(new(ProvenanceChaincode)); err != nil {
		log.Panicf("start chaincode: %v", err)
	}
}
