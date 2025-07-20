package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"dubbo.apache.org/dubbo-go/v3/config"
	_ "dubbo.apache.org/dubbo-go/v3/imports"

	pkg "gitlab.yunshan.net/yunshan/evaluation/eval-bench/client/dubbo"

	hessian "github.com/apache/dubbo-go-hessian2"
)

var (
	survivalTimeout = int(3e9)
)

var dubbo_server_yaml = `
dubbo:
  application:
    name: myApp
    module: opensource
    group: myAppGroup
    organization: dubbo
    owner: laurence
    version: v1
    environment: pro
  protocols:
    dubbo:
      name: dubbo
      port: 20000
  provider:
    services:
      UserProvider:
        interface: org.apache.dubbo.sample.UserProvider
        registry-ids: demoZK
        protocol: dubbo
        loadbalance: random
        warmup: 100
        cluster: failover
        methods:
        - name: GetUser
          retries: 3
          loadbalance: random
        - name: GetUsers
          retries: 3
          loadbalance: random
  logger:
    zap-config:
      level: info
`

var (
	userMap = make(map[string]pkg.User)
)

func init() {
	userMap["000"] = pkg.User{
		ID: "000", Name: "Foo", Age: 31,
		Sex: pkg.MAN,
	}
	userMap["001"] = pkg.User{ID: "001", Name: "Bar", Age: 18, Sex: pkg.MAN}
	userMap["002"] = pkg.User{ID: "002", Name: "Foo-Bar", Age: 20, Sex: pkg.WOMAN}
	userMap["003"] = pkg.User{ID: "113", Name: "Bar-Foo", Age: 30, Sex: pkg.WOMAN}
	for k, v := range userMap {
		v.Time = time.Now()
		userMap[k] = v
	}
}

// need to setup environment variable "DUBBO_GO_CONFIG_PATH" to "conf/dubbogo.yml" before run
func main() {

	hessian.RegisterJavaEnum(pkg.Gender(pkg.MAN))
	hessian.RegisterJavaEnum(pkg.Gender(pkg.WOMAN))
	hessian.RegisterPOJO(&pkg.User{})
	config.SetProviderService(&UserProvider{})

	config.Load(config.WithBytes([]byte(dubbo_server_yaml)))

	initSignal()
}

func initSignal() {
	signals := make(chan os.Signal, 1)
	// It is not possible to block SIGKILL or syscall.SIGSTOP
	signal.Notify(signals, os.Interrupt, syscall.SIGHUP, syscall.SIGQUIT, syscall.SIGTERM)
	for {
		sig := <-signals
		log.Printf("get signal %s", sig.String())
		switch sig {
		case syscall.SIGHUP:
			// reload()
		default:
			time.AfterFunc(time.Duration(survivalTimeout), func() {
				log.Printf("app exit now by force...")
				os.Exit(1)
			})

			// The program exits normally or timeout forcibly exits.
			fmt.Println("provider app exit now...")
			return
		}
	}
}

// --- UserProvider --- //
type UserProvider struct {
	CommonUserProvider
}

// --- CommonUserProvider --- //
type CommonUserProvider struct {
}

func (u *CommonUserProvider) getUser(userID string) (*pkg.User, error) {
	if user, ok := userMap[userID]; ok {
		return &user, nil
	}

	return nil, fmt.Errorf("invalid user id:%s", userID)
}

func (u *CommonUserProvider) GetUser(ctx context.Context, req *pkg.User) (*pkg.User, error) {
	var (
		err  error
		user *pkg.User
	)

	log.Printf("req:%#v", req)
	user, err = u.getUser(req.ID)
	if err == nil {
		log.Printf("rsp:%#v", user)
	}
	return user, err
}

func (u *CommonUserProvider) GetUsers(req []string) ([]*pkg.User, error) {
	var err error

	log.Printf("req:%s", req)
	user, err := u.getUser(req[0])
	if err != nil {
		return nil, err
	}
	log.Printf("user:%v", user)
	user1, err := u.getUser(req[1])
	if err != nil {
		return nil, err
	}
	log.Printf("user1:%v", user1)

	return []*pkg.User{user, user1}, err
}
