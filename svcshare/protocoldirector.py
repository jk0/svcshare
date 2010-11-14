import logging
import threading
import time

from svcshare import clientqueue
from svcshare import exc
from svcshare import msgtypes
from svcshare import network


class ProtocolDirector(network.Network.Notifiee):
  # Protocol version.
  VERSION = 2

  class Notifiee(object):
    def __init__(self):
      self._notifier = None

    def notifierIs(self, notifier):
      if self._notifier is not None:
        notifier._notifiees.remove(self)
      self._notifier = notifier
      notifier._notifiees.append(self)

    def onJoinEvent(self, name):
      pass

    def onLeaveEvent(self, name):
      pass

    def onQueueStatus(self, clientQueue):
      pass

    def onLockStatus(self, lockInfo):
      pass

  def __init__(self, net, client):
    network.Network.Notifiee.__init__(self)
    self.notifierIs(net)
    self._client = client
    self._net = net
    self._notifiees = []
    self._logger = logging.getLogger('ProtocolDirector')

    if net and client:
      self._broadcasterThread = threading.Thread(target=self._broadcaster)
      self._broadcasterThread.daemon = True
      self._broadcasterThread.start()

  def _sendQueueStatus(self):
    queueString = self._client.queue().string()
    msg = '%d %s' % (self._client.queue().items(), queueString)
    self._sendControlMessage(msgtypes.QUEUESTATUS, msg)

  def _sendControlMessage(self, type, message=None):
    self._net.controlMessageIs(self.VERSION, type, message)

  def _broadcaster(self):
    time.sleep(5)
    oldQueue = self._client.queue()
    while True:
      if self._client.queue() != oldQueue:
        self._sendQueueStatus()
        oldQueue = self._client.queue()
      time.sleep(10)

  def _doNotification(self, methodName, *args):
    for notifiee in self._notifiees:
      method = getattr(notifiee, methodName, None)
      if method is not None:
        method(*args)

  def network(self):
    return self._net

  def onJoinEvent(self, name):
    self._sendQueueStatus()

  def onLeaveEvent(self, name):
    self._doNotification('onLeaveEvent', name)

  def onControlMessage(self, name, version, type, message=None):
    # TODO(ms): logging needed here; also magic number
    if version != 2:
      return

    if type == msgtypes.QUEUESTATUS:
      self._doNotification('onQueueStatus', name, None)
    elif type == msgtypes.LOCKSTATUS:
      self._doNotification('onLockStatus', name, None)
