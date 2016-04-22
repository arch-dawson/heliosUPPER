import time
import queue

def main(capt_cmd, cameras):
	# Initialize initial photo capture rate
	rate = 3;
	while True:
		if (capt_cmd.empty() == false):
			cmd = capt_cmd.get()
			if type(cmd) is bytes:
				packet = hex(int.from_bytes(cmd, byteorder = 'big'))
            	## This is where the command is parsed and the rate is changed if necessary 	

        # Take photo 
		cameras.science()

		#downlink.put(["AD", "CP", "Science Image Taken"])
		# Sleep for time equal to rate
		time.sleep(rate)


		