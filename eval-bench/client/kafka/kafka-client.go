package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/Shopify/sarama"
)

type KafkaClient struct {
	isReady bool

	LatencyChan    chan *time.Duration
	ErrLatencyChan chan *time.Duration

	Addrs         []string
	Topic         string
	Group         string
	producer      *sarama.SyncProducer
	consumer      *sarama.Consumer
	consumerGroup *sarama.ConsumerGroup
	config        *sarama.Config
}

func (kc *KafkaClient) Property() {
	fmt.Printf("KafkaClient Property: \n")
	fmt.Printf("KafkaClient.Addrs: %v\n", kc.Addrs)
	fmt.Printf("KafkaClient.Topic: %v\n", kc.Topic)
	fmt.Printf("KafkaClient.Group: %v\n", kc.Group)
}

func (kc *KafkaClient) InitClient() {
	// Configuration
	kc.config = sarama.NewConfig()
	kc.config.Consumer.Return.Errors = true
	kc.config.Producer.Return.Successes = true

	var err error
	// Create a new producer
	kc.producer, err = sarama.NewSyncProducer(kc.Addrs, kc.config)
	if err != nil {
		fmt.Printf("Error creating kafka producer: %v\n", err)
		os.Exit(1)
	}

	// Create a new consumer
	kc.consumer, err = sarama.NewConsumer(kc.Addrs, nil)
	if err != nil {
		fmt.Printf("Error creating kafka consumer: %v\n", err)
		os.Exit(1)
	}
	consumerHandler := ConsumerHandler{}
	err = kc.consumer.SubscribeTopics([]string{kc.Topic}, &consumerHandler)
	if err != nil {
		fmt.Printf("Error subscribing to topics: %v\n", err)
		os.Exit(1)
	}
	// Kafka consumer group
	kc.consumerGroup, err := sarama.NewConsumerGroup(kc.Addrs, kc.Group, config)
	if err != nil {
		log.Fatal(err)
	}
}

func (kc *KafkaClient) IsReady() bool {
	return kc.isReady
}

func (kc *KafkaClient) Exec() error {
	kc.Get()
	return nil
}

func (kc *KafkaClient) Get() {
	go produceMessages(producer)
	// Consume messages
	go consumeMessages(consumerHandler)
}

func (kc *KafkaClient) Close() {
	if kc.producer != nil {
		kc.producer.Close()
	}
	if kc.consumer != nil {
		kc.consumer.Close()
	}
}

// ConsumerHandler is a simple implementation of sarama.ConsumerGroupHandler
type ConsumerHandler struct{}

func (h *ConsumerHandler) Setup(sarama.ConsumerGroupSession) error   { return nil }
func (h *ConsumerHandler) Cleanup(sarama.ConsumerGroupSession) error { return nil }
func (h *ConsumerHandler) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	for message := range claim.Messages() {
		fmt.Printf("Received message: Topic=%s, Partition=%d, Offset=%d, Key=%s, Value=%s\n",
			message.Topic, message.Partition, message.Offset, string(message.Key), string(message.Value))
		session.MarkMessage(message, "")
	}
	return nil
}

func (kc *KafkaClient) produceMessages(producer sarama.AsyncProducer) {
	// Produce a message
	message := &sarama.ProducerMessage{
		Topic: kc.Topic,
		Key:   sarama.StringEncoder("key"),
		Value: sarama.StringEncoder(fmt.Sprintf("Hello Kafka at %s", time.Now().Format(time.Stamp))),
	}
	producer.Input() <- message
}

func (kc *KafkaClient) consumeMessages(consumerHandler ConsumerHandler) {

	// Handle errors
	go func() {
		for err := range consumerGroup.Errors() {
			log.Printf("Error: %s\n", err)
		}
	}()
	// Consume messages
	err := kc.consumerGroup.Consume(context.Background(), []string{kc.Topic}, consumerHandler)
	if err != nil {
		log.Printf("Error: %s\n", err)
	}
}
