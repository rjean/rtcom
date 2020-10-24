=====
Usage
=====

To use RealTimeCommunication in a project::

    from rtcom import RealTimeCommunication

In order to broadcast information to other devices on the network::

    with RealTimeCommunication("rpi") as rtcom:
        i = 0
        while(True):
            rtcom.broadcast_endpoint("heartbeat", i)
            i+=1
            sleep(0.1)

In order to receive information from the device "rpi" on the device "pc"::

    with RealTimeCommunication("pc") as rtcom:
        while(True):
            print(rtcom["rpi"]["heartbeat])

Assuming that the first program runs on an embedded device, such as a Raspberry Pi, and the second device will
display the heartbeat from the "rpi". rtcom will handle synchronisation between the two devices. A periodical thread
retransmits the information over and over again in UDP broadcasts. 

To send binary data, such as a JPEG image::
    
    rtcom.broadcast_endpoint("binary_data", bytes([1,2,3,4]), encoding="binary")

For more example, see the unit tests. For a complete example for broadcasting a real-time video feed in MJPEG, see 
the video_reader and video_writer in the example folder.


