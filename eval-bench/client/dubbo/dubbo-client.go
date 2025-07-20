package dubbo

import (
	"context"
	"log"
	"strings"
	"time"

	"dubbo.apache.org/dubbo-go/v3/config"
	_ "dubbo.apache.org/dubbo-go/v3/imports"

	hessian "github.com/apache/dubbo-go-hessian2"
)

var dubbo_client_yaml = `
dubbo:
  application:
    name: myApp
    module: opensource
    group: myAppGroup
    organization: dubbo
    owner: laurence
    version: v1
    environment: pro
  consumer:
    references:
      UserProvider:
        protocol: dubbo
        interface: org.apache.dubbo.sample.UserProvider
        registry-ids: demoZK
        cluster: failover
        url: "dubbo://${dubbo.registry.address}:20000"
        methods:
        - name: GetUser
          retries: 3
        - name: GetUsers
          retries: 3
`

type DubboClient struct {
	isReady bool

	LatencyChan    chan *time.Duration
	ErrLatencyChan chan *time.Duration

	Addr string

	userProvider *UserProvider
}

func (dc *DubboClient) InitClient() {
	dc.userProvider = &UserProvider{}
	hessian.RegisterJavaEnum(MAN)
	hessian.RegisterJavaEnum(WOMAN)
	hessian.RegisterPOJO(&User{})

	config.SetConsumerService(dc.userProvider)
	dubbo_client_yaml = strings.Replace(dubbo_client_yaml, "${dubbo.registry.address}", dc.Addr, -1)
	err := config.Load(config.WithBytes([]byte(dubbo_client_yaml)))
	if err != nil {
		log.Fatal(err)
	}
	dc.isReady = true
}

func (dc *DubboClient) Property() {
	log.Printf("DubboClient Property:")
	log.Printf("Addr: %s", dc.Addr)
}

func (dc *DubboClient) Close() {
}

func (dc *DubboClient) IsReady() bool {
	return dc.isReady
}

func (dc *DubboClient) Exec() error {
	start := time.Now()
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()

	err := dc.getUser(ctx)
	latency := time.Since(start)
	if err != nil {
		dc.ErrLatencyChan <- &latency
		log.Printf("unable to send message: %v", err)
	} else {
		dc.LatencyChan <- &latency
	}
	return err
}

func (dc *DubboClient) getUser(ctx context.Context) error {
	reqUser := &User{
		ID: "003",
	}
	_, err := dc.userProvider.GetUser(ctx, reqUser)
	if err != nil {
		return err
	}
	_, err = dc.userProvider.GetUsers([]string{"002", "003"})
	return err
}
