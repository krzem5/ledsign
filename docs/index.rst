LEDSign documentation
=====================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

.. autoclass:: ledsign.LEDSign()
   :members:

.. autoclass:: ledsign.LEDSignHardware()
   :members:

.. autoclass:: ledsign.LEDSignSelector()
   :members:

.. autodecorator:: ledsign.LEDSignProgram(device:LEDSignDevice)
   :no-index:

.. autoclass:: ledsign.LEDSignProgram(device:LEDSignDevice,file_path:str)
   :members:
   :special-members: __call__

.. autoclass:: ledsign.LEDSignKeypoint()
   :members:

.. autoexception:: ledsign.LEDSignAccessError
.. autoexception:: ledsign.LEDSignDeviceInUseError
.. autoexception:: ledsign.LEDSignDeviceNotFoundError
.. autoexception:: ledsign.LEDSignProgramError
.. autoexception:: ledsign.LEDSignProtocolError
.. autoexception:: ledsign.LEDSignUnsupportedProtocolError
