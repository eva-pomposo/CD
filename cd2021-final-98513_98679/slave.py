import time
import socket
import selectors
import fcntl
import sys, errno
import os
import base64
from itertools import product
from string import ascii_letters, digits
from server import const
import struct
import json



class Slave:
    address=[]

    def __init__(self):
        """DEFINIG VARIABLES"""
        self.host='172.17.0.2'
        #self.host='127.0.1.1' #colocar o endereço do server
        self.port=8000
        self.posicao=0
        #self.n_slaves=1
        
       

        
        """Testing multicast sockets sending"""
        self.MCAST_GRP = '224.1.1.1'
        self.MCAST_PORT = 5007
        self.MULTICAST_TTL = 2

        #self.sock_multicast_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        #self.sock_multicast_send.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self.MULTICAST_TTL)
        #self.sock_multicast_send.sendto("Recent connected".encode('utf-8'), (self.MCAST_GRP, self.MCAST_PORT))

    
    def connect(self):    
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        print("Connected to" , self.host,":",self.port, " in ", self.sock)
        #password_size+=1
        #self.pass_tamanho = password_size
        #print('TAMNANHO ', self.pass_tamanho)

        
        
        
        """SOCKETS MULTICAST DE ENVIO"""
        self.sock_multicast_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock_multicast_send.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self.MULTICAST_TTL)
        print("Get peer name" ,socket.gethostbyname(socket.gethostname())) 
        Slave.address.append(socket.gethostbyname(socket.gethostname())) #MEU IP 
        self.pass_tamanho=len(Slave.address)
        msg_connect = json.dumps({"command":"register", "ip": socket.gethostbyname(socket.gethostname())}).encode('utf-8')
        self.sock_multicast_send.sendto(msg_connect, (self.MCAST_GRP, self.MCAST_PORT))
        


    def send_msg(self, msg,conn):
        conn.send(msg)
        
    
    def encode64(self,password) -> str:
        string_pass = ('root:'+password).encode('utf-8')
        pass_64 = base64.b64encode(string_pass).decode('utf-8')
        return pass_64


    def combinations(self, length):
        lst=[]
        if (length>4):
            print("Getting  all combinations")
        for i in product(ascii_letters + digits, repeat=length):
            lst.append(''.join(i))
        return lst
    
    
    def rcv_from_slaves(self):
        """create multicast sockets to receive data"""
        self.sock_multicast_receive = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock_multicast_receive.settimeout(0)                
        self.sock_multicast_receive.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock_multicast_receive.bind(('', self.MCAST_PORT))
        mreq = struct.pack("4sl", socket.inet_aton(self.MCAST_GRP), socket.INADDR_ANY)
        self.sock_multicast_receive.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    
    
    def rcv_multicast(self): 
        """receber dos outros slaves"""
        try:
            json_string = self.sock_multicast_receive.recv(10240).decode('utf-8')
            message = json.loads(json_string)
            if message['command'] == 'register':
                #self.n_slaves+=1
                msg_connect = json.dumps({"command":"register", "ip": socket.gethostbyname(socket.gethostname())}).encode('utf-8')
                self.sock_multicast_send.sendto(msg_connect, (self.MCAST_GRP, self.MCAST_PORT))
                if message["ip"] not in Slave.address:
                    Slave.address.append(message["ip"])

            elif message['command'] == 'found':
                self.sock_multicast_receive.close()
                self.sock_multicast_send.close()
                self.sock.close()
                self.continuar = False
            elif message['command'] == 'try':
                self.i=message['option']
                self.sock_uni.close()
            return message
        except socket.error:
            pass


    def loop(self):
        self.rcv_from_slaves()
        #time.sleep(5)
        comb = self.combinations(self.pass_tamanho)
        self.i=0
        self.continuar = True
        while self.continuar:
            """receber das sockets multicast"""
            mensagem = self.rcv_multicast()
            self.rcv_from_slaves()

            """HTTP protocol and turn sockets on"""
            self.msg= "GET / HTTP/1.1\nHost: "+self.host+" : "+str(self.port)+"\n"
            self.msg += "Authorization: Basic "+str(self.encode64(comb[self.i]))+"\n\n"
            self.send_msg(self.msg.encode('utf-8'),self.sock)
            print("Trying... ", comb[self.i])
            received=self.sock.recv(1024).decode('utf-8')

            if "OK" in received:
                msg_ok = {'command': 'found', 'password': comb[self.i]}
                if len(Slave.address)>1:
                    msg_ok_encode=json.dumps(msg_ok).encode('utf-8')
                    self.sock_multicast_send.sendto(msg_ok_encode, (self.MCAST_GRP, self.MCAST_PORT))
                print(msg_ok)
                break
            elif received[-1] == "\n":
                b=self.sock.recv(1024).decode('utf-8')
                received+=b
                t=1
                for addr in Slave.address:
                    if (addr != socket.gethostbyname(socket.gethostname())):
                        self.sockets_slave_send(addr,8000,t)
                        t+=1
            elif mensagem['register']:
                msg_connect = json.dumps({"command":"register", "ip": socket.gethostbyname(socket.gethostname())}).encode('utf-8')
                self.sock_multicast_send.sendto(msg_connect, (self.MCAST_GRP, self.MCAST_PORT))
            print("------------------------------",self.pass_tamanho)
            self.i+=1
            self.posicao+=1
            if (self.posicao%const.MIN_TRIES==0 and self.posicao!=0):
                time.sleep((const.COOLDOWN_TIME/1000)%60)
            if (len(comb) == self.i):
                self.pass_tamanho+=1
                self.i=0
                comb = self.combinations(self.pass_tamanho)
            

    def sockets_slave_send(self,addr,port,value):
        self.sock_uni = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        self.sock_uni.connect((addr,port))
        mensagem = {"command":"try", "option":self.i+value}
        self.sock_uni.send(json.dumps(mensagem).encode('utf-8'))

        



if __name__ == "__main__":
    
    s = Slave()
    s.connect()
    s.loop()

#{'command': 'register', 'socket',"(host,port)"} -> usado para manter sempre a conexao da rede
#{'command': 'found', 'password': variavel} -> quando descobre a palavra passe
#{'command': 'actual_val', i:variavel} -> quando um tentou

#PROTOCOLO HTTP
    #GET / HTTP/1.1 
    #Host: localhost:8000
    #Authorization: Basic a