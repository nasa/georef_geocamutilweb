# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import zmq
from zmq.eventloop.zmqstream import ZMQStream

from geocamUtil import anyjson as json
from geocamUtil.zmq.util import parseEndpoint, DEFAULT_CENTRAL_RPC_PORT

SUBSCRIBER_OPT_DEFAULTS = {'moduleName': None,
                           'centralPublishEndpoint': 'tcp://127.0.0.1:%d'
                           % (DEFAULT_CENTRAL_RPC_PORT + 1)}


class ZmqSubscriber(object):
    def __init__(self,
                 moduleName,
                 context=None,
                 centralPublishEndpoint=SUBSCRIBER_OPT_DEFAULTS['centralPublishEndpoint']):
        self.moduleName = moduleName

        if context is None:
            context = zmq.Context()
        self.context = context

        self.centralPublishEndpoint = parseEndpoint(centralPublishEndpoint,
                                                    defaultPort=DEFAULT_CENTRAL_RPC_PORT + 1)

        self.handlers = {}
        self.counter = 0

    @classmethod
    def addOptions(cls, parser, defaultModuleName):
        if not parser.has_option('--moduleName'):
            parser.add_option('--moduleName',
                              default=defaultModuleName,
                              help='Name to use for this module [%default]')
        if not parser.has_option('--centralPublishEndpoint'):
            parser.add_option('--centralPublishEndpoint',
                              default=SUBSCRIBER_OPT_DEFAULTS['centralPublishEndpoint'],
                              help='Endpoint where central publishes messages [%default]')

    @classmethod
    def getOptionValues(cls, opts):
        result = {}
        for key in SUBSCRIBER_OPT_DEFAULTS.iterkeys():
            val = getattr(opts, key, None)
            if val is not None:
                result[key] = val
        return result

    def start(self):
        sock = self.context.socket(zmq.SUB)
        self.stream = ZMQStream(sock)
        self.stream.setsockopt(zmq.IDENTITY, self.moduleName)
        self.stream.connect(self.centralPublishEndpoint)
        self.stream.on_recv(self.routeMessage)

    def routeMessage(self, messages):
        for msg in messages:
            colonIndex = msg.find(':')
            topic = msg[:(colonIndex + 1)]
            body = msg[(colonIndex + 1):]
            obj = json.loads(body)

            # fast exact match
            topicRegistry = self.handlers.get(topic, None)

            # prefix match
            if topicRegistry is None:
                for topicPrefix, registry in self.handlers.iteritems():
                    if topic.startswith(topicPrefix):
                        topicRegistry = registry
                        break

            for handler in topicRegistry.itervalues():
                handler(topic, obj)

    def subscribe(self, topic, handler):
        topicRegistry = self.handlers.setdefault(topic, {})
        if not topicRegistry:
            self.stream.setsockopt(zmq.SUBSCRIBE, topic)
        handlerId = self.counter
        self.counter += 1
        topicRegistry[handlerId] = handler
        return handlerId

    def unsubscribe(self, topic, handlerId):
        topicRegistry = self.handlers[topic]
        del topicRegistry[handlerId]
        if not topicRegistry:
            self.stream.setsockopt(zmq.UNSUBSCRIBE, topic)
