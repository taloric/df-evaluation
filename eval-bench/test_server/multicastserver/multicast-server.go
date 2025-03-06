package main

import (
	"flag"
	"fmt"
	"net"
	"strconv"
	"strings"
)

var (
	fmulticastGroup = flag.String("group", "", "Multicast Address, Example: 224.1.1.1:5050")
	fiface          = flag.String("ifaces", "", "Interface")
	fifaceRange     = flag.String("ifaceRange", "", "Interface Range, Example: eth,0-1")
)

func main() {
	// 接口
	flag.Parse()
	fmt.Println(*fmulticastGroup, *fiface)
	address, err := net.ResolveUDPAddr("udp", *fmulticastGroup)
	if err != nil {
		fmt.Println(*fmulticastGroup, err)
		return
	}
	ifs := []string{}
	if *fiface != "" {
		ifs = strings.Split(*fiface, ",")
	}
	if *fifaceRange != "" {
		ranges := strings.Split(*fifaceRange, ",")
		ifPrefix := ranges[0]
		StartAndEnd := strings.Split(ranges[1], "-")
		start, err := strconv.Atoi(StartAndEnd[0])
		end, err := strconv.Atoi(StartAndEnd[1])
		if err != nil {
			fmt.Println(*fifaceRange, err)
			return
		}
		for i := start; i <= end; i++ {
			ifs = append(ifs, ifPrefix+strconv.Itoa(i))
		}
	}

	for _, fiface := range ifs {
		iface, err := net.InterfaceByName(fiface) // 根据实际接口名称修改
		if err != nil {
			fmt.Println(fiface, err)
			continue
		}
		// 加入组播组
		conn, err := net.ListenMulticastUDP("udp", iface, address)
		if err != nil {
			fmt.Println(err)
			return
		}
		defer conn.Close()
		go func() {
			// 循环来接收数据
			for {
				fmt.Println("Listening on interface", iface.Name)
				buffer := make([]byte, 1024)
				n, addr, err := conn.ReadFromUDP(buffer)
				if err != nil {
					fmt.Println(err)
					continue
				}
				fmt.Printf("Received %d bytes from %s\n", n, addr)
			}
		}()
	}
	<-make(chan struct{})
}
