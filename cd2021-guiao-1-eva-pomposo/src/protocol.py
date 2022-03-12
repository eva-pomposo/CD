"""Protocol for chat server - Computação Distribuida Assignment 1."""
import json
from datetime import datetime
from socket import socket
import struct


class Message:
    """Message Type."""
    def __init__(self, command):
        self.command = command

    def __str__(self):
        return f'{{"command": "{self.command}"'

    
class JoinMessage(Message):
    """Message to join a chat channel."""
    def __init__(self, command, channel):
        super().__init__(command)
        self.channel = channel

    def __str__(self):
        return f'{super().__str__()}, "channel": "{self.channel}"}}'


class RegisterMessage(Message):
    """Message to register username in the server."""
    def __init__(self, command, user):
        super().__init__(command)
        self.user = user

    def __str__(self):
        return f'{super().__str__()}, "user": "{self.user}"}}'


    
class TextMessage(Message):
    """Message to chat with other clients."""
    def __init__(self,command,message,channel):
        super().__init__(command)
        self.message = message
        self.channel = channel

    def __str__(self):
        if(self.channel!=None):
            return f'{super().__str__()}, "channel": "{self.channel}", "message": "{self.message}", "ts": {int(datetime.now().timestamp())}}}'
        else:
            return f'{super().__str__()}, "message": "{self.message}", "ts": {int(datetime.now().timestamp())}}}'


class CDProto:
    """Computação Distribuida Protocol."""

    @classmethod
    def register(cls, username: str) -> RegisterMessage:
        """Creates a RegisterMessage object."""
        return RegisterMessage("register",username)

    @classmethod
    def join(cls, channel: str) -> JoinMessage:
        """Creates a JoinMessage object."""
        return JoinMessage("join", channel)

    @classmethod
    def message(cls, message: str, channel: str = None) -> TextMessage:
        """Creates a TextMessage object."""
        return TextMessage("message", message, channel)

    @classmethod
    def send_msg(cls, connection: socket, msg: Message):
        """Sends through a connection a Message object."""

        #Construir a msg em formato json
        if type(msg) is RegisterMessage:
            msg_json = json.dumps({"command": msg.command, "user": msg.user}).encode('utf-8')
        elif type(msg) is JoinMessage:
            msg_json = json.dumps({"command": msg.command, "channel": msg.channel}).encode('utf-8')
        elif type(msg) is TextMessage:
            if(msg.channel!=None):
                msg_json = json.dumps({"command": msg.command, "message": msg.message, "channel": msg.channel, "ts":datetime.now().timestamp()}).encode('utf-8')
            else:
                msg_json = json.dumps({"command": msg.command, "message": msg.message, "ts":datetime.now().timestamp()}).encode('utf-8')


        header = len(msg_json).to_bytes(2, "big")   #tamanho da mensagem em 2 bytes big endian
        connection.sendall(header + msg_json)       #enviar à socket que está ligada o tamanho + a mensagem

    @classmethod
    def recv_msg(cls, connection: socket) -> Message:
        """Receives through a connection a Message object."""
        
        header_aux = connection.recv(2)                         #ler 2 bytes da mensagem recebida na socket connection
        if not header_aux:                                      
            raise ConnectionError()                           

        header = int.from_bytes(header_aux, "big")              #cabeçalho da mensagem em int
        msg = connection.recv(header).decode('UTF-8')           #ler mensagem recebida na socket connection

        try:
            comando = json.loads(msg)["command"]

            if(comando=="message"):
                mensagem = json.loads(msg)["message"]
                if("channel" in json.loads(msg)):
                    channel = json.loads(msg)["channel"]
                    return CDProto.message(mensagem,channel)
                else:
                    return CDProto.message(mensagem)
                
            elif(comando=="join"):
                channel = json.loads(msg)["channel"]
                return CDProto.join(channel)
            elif(comando=="register"):
                name = json.loads(msg)["user"]
                return CDProto.register(name)
        except:
            raise CDProtoBadFormat()                            #caso alguma chave nao exista em json.loads(msg) chamar CDProtoBadFormat                 


class CDProtoBadFormat(Exception):
    """Exception when source message is not CDProto."""

    def __init__(self, original_msg: bytes=None) :
        """Store original message that triggered exception."""
        self._original = original_msg

    @property
    def original_msg(self) -> str:
        """Retrieve original message as a string."""
        return self._original.decode("utf-8")

