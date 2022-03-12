"""CD Chat client program"""
import logging
import socket
import selectors
import sys
import fcntl
import os

from .protocol import CDProto, CDProtoBadFormat

logging.basicConfig(filename=f"{sys.argv[0]}.log", level=logging.DEBUG)

class Client:
    """Chat Client process."""

    def __init__(self, name: str = "Foo"):
        """Initializes chat client."""
        self.name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # criar socket do cliente
        self.sel = selectors.DefaultSelector()                          #criar seletor
        self.channel = None                                             #definir o canal inicialmente como None
    
    def connect(self):
        """Connect to chat server and setup stdin flags."""
        self.sock.connect(('localhost',1027))                           #conectar a scoket ao servidor 
        self.sel.register(self.sock, selectors.EVENT_READ, self.read)   #registar sock em sel, chamar funçao read quando o seletor detetar eventos read em sock

        #Enviar mensagem de RegisterMessage ao servidor:
        msg = CDProto.register(self.name)
        CDProto.send_msg(self.sock, msg)

    def read(self, conn, mask):
        msg = CDProto.recv_msg(self.sock)                               #ler a mensagem recebida na socket sock
        logging.debug('received "%s', msg)
        if(msg.command=="message"):
            print("\r<" + msg.message)                                  #fazer print da mensagem
        elif(msg.command=="join"):
            print("\rEntrou no canal: " + msg.channel)
        else:
            print("\rRegistou-se no servidor, com o nome: " + msg.user)

    # function to be called when enter is pressed
    def got_keyboard_data(self,stdin,mask):
        frase = stdin.read()

        if(frase[0:6]=="/join "):
            msg = CDProto.join(frase[6:-1])
            CDProto.send_msg(self.sock, msg)                    #enviar mensagem de JoinMessage ao servidor
            self.channel = msg.channel                          #atualizar ultimo canal que fez join
        elif(frase=="exit\n"):
            sys.exit("Exit!") 
            self.sock.close()                                  
        else:
            msg = CDProto.message(frase[:-1],self.channel)      
            CDProto.send_msg(self.sock, msg)                    #enviar mensagem de TextMessage ao servidor

    def loop(self):
        """Loop indefinetely."""
        # set sys.stdin non-blocking
        orig_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)

        # register event
        self.sel.register(sys.stdin, selectors.EVENT_READ, self.got_keyboard_data)
        while True:
            sys.stdout.write('>')
            sys.stdout.flush()
            for k, mask in self.sel.select():
                callback = k.data
                callback(k.fileobj,mask)
