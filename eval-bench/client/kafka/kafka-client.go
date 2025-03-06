package kafka

import (
	"fmt"
	"log"
	"time"
	"github.com/IBM/sarama"
)

type KafkaClient struct {
	isReady bool

	LatencyChan    chan *time.Duration
	ErrLatencyChan chan *time.Duration

	Addr          string
	Addrs         []string
	Topic         string
	producer      sarama.SyncProducer
	config        *sarama.Config
}

func (kc *KafkaClient) Property() {
	fmt.Printf("KafkaClient Property: \n")
	fmt.Printf("KafkaClient.Addr: %v\n", kc.Addr)
	fmt.Printf("KafkaClient.Topic: %v\n", kc.Topic)
}

func (kc *KafkaClient) InitClient() {
	kc.Addrs = []string{kc.Addr}
	// Configuration
	kc.config = sarama.NewConfig()
	kc.config.Consumer.Return.Errors = true
	kc.config.Producer.Return.Successes = true
	kc.config.ClientID = "eb"
	// sarama.Logger = log.New(os.Stdout, "[Sarama] ", log.LstdFlags)

	var err error
	// Create a new producer
	kc.producer, err = sarama.NewSyncProducer(kc.Addrs, kc.config)
	if err != nil {
		log.Fatal("Error creating kafka producer: ", err)
	}
	kc.isReady = true
}

func (kc *KafkaClient) IsReady() bool {
	return kc.isReady
}

func (kc *KafkaClient) Exec() error {
	kc.produceMessages()
	return nil
}

func (kc *KafkaClient) Close() {
	if kc.producer != nil {
		kc.producer.Close()
	}
}

// ConsumerHandler is a simple implementation of sarama.ConsumerGroupHandler

func (kc *KafkaClient) produceMessages() {
	// Produce a message
	message := &sarama.ProducerMessage{
		Topic: kc.Topic,
		Key:   sarama.StringEncoder("key"),
		Value: sarama.StringEncoder(fmt.Sprintf("H K at %d", time.Now().UnixNano())),
	}
	start := time.Now()
	_, _, err := kc.producer.SendMessage(message)
	latency := time.Since(start)
	if err != nil {
		kc.ErrLatencyChan <- &latency
		log.Printf("Failed to send message: %v", err)
	} else {
		kc.LatencyChan <- &latency
	}
}

