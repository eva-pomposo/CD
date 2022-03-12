"""CD Chat server program."""
import logging
import socket
import selectors

from .protocol import CDProto, CDProtoBadFormat

logging.basicConfig(filename="server.log", level=logging.DEBUG)

class Server:
    """Chat Server process."""

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # criar socket-servidor  
        self.sock.bind(('localhost',1027))                              #ligar sock-servidor à host: localhost e à porta 1027
        self.sock.listen(10)                                            
        self.sel = selectors.DefaultSelector()                          
        self.sel.register(self.sock, selectors.EVENT_READ, self.accept) #registar sock em sel, chamar funçao accept quando o seletor detetar eventos read em sock
        self.conns = {}                                                 #conns dicionário. Chave: socket ligada a um cliente; valor: lista de canais do cliente associado  

    def accept(self, sock, mask):
        conn, addr = sock.accept()                                  #Ligar-se ao cliente, criando uma nova socket no servidor (conn) que está ligado ao cliente     
        print('accepted', conn, 'from', addr)
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)    
        self.conns[conn] = [None]                                   #Defenir a socket ligada ao cliente como chave de conns, com valor uma lista sem canais
                                                                    # Após um cliente fazer um register, o cliente nao estará em nenhum canal. None representará o sem canal

    def read(self,conn, mask):
        try:
            msg = CDProto.recv_msg(conn)                    #Criar e ler a mensagem recebida na socket conn
            logging.debug('received "%s', msg)
            
            print('echoing', str(msg), 'to', conn)
                
            if(msg.command=="join"):                        #verificar se o command da mensagem recebida foi join
                if(None in self.conns[conn]):               
                    self.conns[conn].remove(None)           #retirar None da lista de canais se estiver lá
                if(msg.channel not in self.conns[conn]):   
                    self.conns[conn].append(msg.channel)    #adicionar canal na lista de canais se nao estiver lá
                CDProto.send_msg(conn, msg)                 #conn envia a mensagem para a socket ligada
            elif(msg.command=="message"):                   #verificar se o command da mensagem recebida foi message
                for key, value in self.conns.items():       
                    if(msg.channel in value):               #apenas as sockets que contêm na sua lista de canais o canal da mensagem, vao enviar a mensagem 
                        CDProto.send_msg(key,msg)
            elif(msg.command=="register"):                  #verificar se o command da mensagem recebida foi register
                CDProto.send_msg(conn,msg)                  #conn envia a mensagem para a socket ligada
        except ConnectionError:                             #verificar se o bloco de código do try captou uma execeçao ConnectionError
            print('closing', conn)                          
            self.sel.unregister(conn)                       
            self.conns.pop(conn)                            #retirar conn como chave (e consequentemente o respectivo valor) do dicionário conns 
            conn.close()                                    

    def loop(self):
            """Loop indefinetely."""
            while True:
                events = self.sel.select()
                for key, mask in events:
                    callback = key.data
                    callback(key.fileobj, mask)