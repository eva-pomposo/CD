"""Message Broker"""
import enum
import socket
import selectors
import json
import pickle
import xml
import xml.etree.ElementTree as XM


from typing import Dict, List, Any, Tuple

class Serializer(enum.Enum):
    """Possible message serializers."""

    JSON = 0
    XML = 1
    PICKLE = 2


class Broker:
    """Implementation of a PubSub Message Broker."""

    def __init__(self):
        """Initialize broker."""
        self.canceled = False   
        self._host = "localhost"
        self._port = 5000
        self.usersSerializer = {}                                       #key -> socket; value-> serializer method
        self.topic_usersSerializer = {}                                 #key -> topico; valor -> tuple list w/ (socket address, serializer method)
        self.msg_topics={}                                              #key -> topic; value -> last message of that topic
        self.topics_producer = []                                       #topic list where producer already sended messages 
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   #Create socket-broker
        self.sock.bind((self._host,self._port))                         
        self.sock.listen(10)
        self.sel = selectors.DefaultSelector()
        self.sel.register(self.sock, selectors.EVENT_READ, self.accept) #registar sock em sel, chamar funçao accept quando o seletor detetar eventos read em sock

    def accept(self, sock, mask):
        """receives connection and decode message depending from its serialization method, used for new connections"""
        conn, addr = sock.accept()                                  
        print('accepted', conn, 'from', addr)
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)

        try:
            header_aux = conn.recv(2)                        
            if not header_aux:                                      
                raise ConnectionError()                           

            header = int.from_bytes(header_aux, "big")  
            data = conn.recv(header).decode('UTF-8')
            if data:
                if json.loads(data)["Serializer"] == 'JSONQueue':
                    self.usersSerializer[conn] = Serializer.JSON
                elif json.loads(data)["Serializer"] == 'XMLQueue':
                    self.usersSerializer[conn] = Serializer.XML
                elif json.loads(data)["Serializer"] == 'PickleQueue':
                    self.usersSerializer[conn] = Serializer.PICKLE
        except ConnectionError: 
            print('closing', conn)                          
            self.sel.unregister(conn)                       
            conn.close() 

    def read(self,conn, mask):
        """verify the serialization method for each conn and decode it, used for 'old' connections """
        try:
            header_aux = conn.recv(2)                        
            if not header_aux:                                      
                raise ConnectionError()                           

            header = int.from_bytes(header_aux, "big")  
            data = conn.recv(header)

            if data:
                if conn in self.usersSerializer:
                    if self.usersSerializer[conn] == Serializer.JSON:
                        method, topic, msg = self.decodeJSON(data)
                    elif self.usersSerializer[conn] == Serializer.XML:
                        method, topic, msg = self.decodeXML(data)
                    elif self.usersSerializer[conn] == Serializer.PICKLE:
                        method, topic, msg = self.decodePICKLE(data)

                    if method == 'PUBLISH':
                        self.put_topic(topic, msg)
                    elif method == 'SUBSCRIBE':
                        self.subscribe(topic,conn, self.usersSerializer[conn])
                    elif method == 'CANCEL_SUBSCRIPTION':
                        self.unsubscribe(topic,conn)
                    elif method == 'LIST_TOPICS':
                        self.send_msg(conn,'LIST_TOPICS_REP',topic, self.list_topics())
        except ConnectionError:
            print('closing', conn)
            for i in self.topic_usersSerializer:
                list_users = self.topic_usersSerializer[i]
                for f in list_users:
                    if f[0] == conn:
                        self.topic_usersSerializer[i].remove(f)
                        break

            self.sel.unregister(conn)
            conn.close()

    def list_topics(self) -> List[str]:
        """Returns a list of strings containing all topics."""
        return self.topics_producer

    def get_topic(self, topic):
        """Returns the currently stored value in topic."""
        if topic in self.msg_topics:
            return self.msg_topics[topic] 
        else:
            return None

    #store in topic the value. If the topic is a subtopic from another topic, this topic also receives the value 
    def put_topic(self, topic, value):
        """Store in topic the value."""
        self.msg_topics[topic] = value
        
        #verify if this topic is a subtopic of an existing topic 
        if topic not in self.topics_producer:
            self.topics_producer.append(topic)
            
        self.update_topic_usersSerializer(topic)

        if topic in self.topic_usersSerializer:
            # send to all topics and "super-topics"
            for i in self.list_subscriptions(topic):
                self.send_msg(i[0], 'MESSAGE', topic, value)
        
    def list_subscriptions(self, topic: str) -> List[socket.socket]:
        """Provide list of subscribers to a given topic."""
        if topic in self.topic_usersSerializer:
            return self.topic_usersSerializer[topic]
        return []

    def subscribe(self, topic: str, address: socket.socket, _format: Serializer = None):
        """Subscribe to topic by client in address."""

        self.update_topic_usersSerializer(topic)
        self.topic_usersSerializer[topic].append((address, _format))
        
        if topic in self.msg_topics:
            self.send_msg(address, 'LAST_MESSAGE', topic, self.get_topic(topic))        

    def unsubscribe(self, topic, address):
        """Unsubscribe to topic by client in address."""

        if topic in self.topic_usersSerializer:
            list_users = self.topic_usersSerializer[topic]
            for i in list_users:
                if i[0] == address:
                    self.topic_usersSerializer[topic].remove(i)
                    break

    def update_topic_usersSerializer(self,topic):
        """Update the dict topic_usersSerializer when broker receives a new topic"""

        if topic not in self.topic_usersSerializer:
            self.topic_usersSerializer[topic] = []
            for topico in self.topic_usersSerializer:
                if topic.startswith(topico):
                    for i in self.list_subscriptions(topico):
                        if i not in self.list_subscriptions(topic):
                            self.topic_usersSerializer[topic].append(i)

    def send_msg(self,conn, method, topic, msg):
        """Verify the conn' Serializer method"""
        if self.usersSerializer[conn] == Serializer.JSON:
            message = self.encodeJSON(method,topic,msg) 
        elif self.usersSerializer[conn] == Serializer.XML:
            message = self.encodeXML(method,topic,msg) 
        elif self.usersSerializer[conn] == Serializer.PICKLE:
            message = self.encodePICKLE(method,topic,msg) 
        
        header = len(message).to_bytes(2, "big")   
        conn.send(header + message)       

    def decodeJSON(self, data):
        data = data.decode('utf-8')
        msg = json.loads(data)
        metodo = msg['method']
        topic = msg['topic']
        msg = msg['msg']
        return metodo,topic,msg  

    def encodeJSON(self, method, topic,msg):
        mensagem = {'method':method,'topic':topic,'msg':msg}
        mensagem = json.dumps(mensagem)
        mensagem = mensagem.encode('utf-8')
        return mensagem 

    def decodeXML(self,data):
        data = data.decode('utf-8')
        data = XM.fromstring(data)
        data_temp = data.attrib
        metodo = data_temp['method']
        topic = data_temp['topic']
        msg = data.find('msg').text
        return metodo,topic,msg

    def encodeXML(self,method,topic,msg):
        mensagem = {'method':method,'topic':topic,'msg':msg}
        mensagem = ('<?xml version="1.0"?><data method="%(method)s" topic="%(topic)s"><msg>%(msg)s</msg></data>' % mensagem)
        mensagem = mensagem.encode('utf-8')
        return mensagem

    def encodePICKLE(self,method, topic,msg):
        mensagem = {'method':method,'topic':topic,'msg':msg}
        mensagem = pickle.dumps(mensagem)
        return mensagem

    def decodePICKLE(self,data):
        msg = pickle.loads(data)
        metodo = msg['method']
        topic = msg['topic']
        msg = msg['msg']
        return metodo,topic,msg

    def run(self):
        """Run until canceled."""
        while not self.canceled:
            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
