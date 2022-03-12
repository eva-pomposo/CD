
import socket
import selectors
import json
import pickle
import xml.etree.ElementTree as XM
from broker import Broker

"""Middleware to communicate with PubSub Message Broker."""
from collections.abc import Callable
from enum import Enum
from queue import LifoQueue, Empty
from typing import Any


class MiddlewareType(Enum):
    """Middleware Type."""

    CONSUMER = 1
    PRODUCER = 2


class Queue:
    """Representation of Queue interface for both Consumers and Producers."""

    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
        """Create Queue."""
        self.topic = topic
        self._type = _type
        self.host = 'localhost'
        self.port = 5000
        self.sel = selectors.DefaultSelector()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.sel.register(self.sock, selectors.EVENT_READ, self.pull)

        #Send ACK message to broker, first of all
        msg_json = json.dumps({"method": "ACK", "Serializer": str(self.__class__.__name__)}).encode('utf-8')
        header = len(msg_json).to_bytes(2, "big")   
        self.sock.send(header + msg_json)

        if self._type==MiddlewareType.CONSUMER:
            self.send_msg('SUBSCRIBE', topic)


    def push(self, value):
        """Sends data to broker. """
        self.send_msg('PUBLISH', value)
    
    # protocol used
    def pull(self) -> (str, Any):
        """Waits for (topic, data) from broker.

        Should BLOCK the consumer!"""

        header_aux = self.sock.recv(2)                        
        if not header_aux:                                      
            raise ConnectionError()      

        header = int.from_bytes(header_aux, "big")  
        data = self.sock.recv(header)
        
        if data:            
            method, topic, msg = self.decode(data) 
            return topic, msg
        else:
            pass

    def list_topics(self, callback: Callable):
        """Lists all topics available in the broker."""
        self.send_msg('LIST_TOPICS', '')

    def cancel(self):
        """Cancel subscription."""
        self.send_msg('CANCEL_SUBSCRIPTION', self.topic)

    def send_msg(self, method, msg):
        """Sends through a connection a Message object."""

        message = self.encode(method,self.topic,msg) 
        header = len(message).to_bytes(2, "big")   
        self.sock.send(header + message)       



class JSONQueue(Queue):
    """Queue implementation with JSON based serialization."""
    def __init__(self, topic, _type=MiddlewareType.CONSUMER):  
        super().__init__(topic, _type)

    def decode(self, data):
        data = data.decode('utf-8')
        msg = json.loads(data)
        metodo = msg['method']
        topic = msg['topic']
        msg = msg['msg']
        return metodo,topic,msg  
    
    def encode(self, method, topic,msg):
        mensagem = {'method':method,'topic':topic,'msg':msg}
        mensagem = json.dumps(mensagem)
        mensagem = mensagem.encode('utf-8')
        return mensagem   



class XMLQueue(Queue):
    """Queue implementation with XML based serialization."""
    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
        super().__init__(topic, _type)

    def decode(self,data):
        data = data.decode('utf-8')
        data = XM.fromstring(data)
        data_temp = data.attrib
        metodo = data_temp['method']
        topic = data_temp['topic']
        msg = data.find('msg').text
        return metodo,topic,msg

    def encode(self,method,topic,msg):
        mensagem = {'method':method,'topic':topic,'msg':msg}
        mensagem = ('<?xml version="1.0"?><data method="%(method)s" topic="%(topic)s"><msg>%(msg)s</msg></data>' % mensagem)
        mensagem = mensagem.encode('utf-8')
        return mensagem


class PickleQueue(Queue):
    """Queue implementation with Pickle based serialization."""
    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
        super().__init__(topic, _type)

    def decode(self,data):
        msg = pickle.loads(data)
        metodo = msg['method']
        topic = msg['topic']
        msg = msg['msg']
        return metodo,topic,msg

    def encode(self,method, topic,msg):
        mensagem = {'method':method,'topic':topic,'msg':msg}
        mensagem = pickle.dumps(mensagem)
        return mensagem
    
