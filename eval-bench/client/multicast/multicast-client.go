package multicast

import (
	"bytes"
	"fmt"
	"net"
	"time"
)

type MulticastClient struct {
	isReady bool

	LatencyChan    chan *time.Duration
	ErrLatencyChan chan *time.Duration

	data []byte

	Addr       string
	Client     net.Conn
	Complexity int
	DataSize   int
}

func (mc *MulticastClient) Property() {
	fmt.Printf("MulticastClient Property:\n")
	fmt.Printf("Addr: %s\n", mc.Addr)
	fmt.Printf("Complexity: %d\n", mc.Complexity)
	fmt.Printf("DataSize: %d\n", mc.DataSize)
}

func (mc *MulticastClient) InitClient() {
	var err error
	mc.Client, err = net.Dial("udp", mc.Addr)
	if err != nil {
		fmt.Println(err)
		return
	}
	mc.data = bytes.Repeat([]byte("A"), mc.DataSize)
	mc.isReady = true
}

func (mc *MulticastClient) IsReady() bool {
	return mc.isReady
}

func (mc *MulticastClient) Exec() error {
	_, err := mc.Client.Write(mc.data)
	if err != nil {
		fmt.Println(err)
	}
	return nil
}

func (mc *MulticastClient) Close() {
	if mc.Client != nil {
		mc.Client.Close()
	}
}
