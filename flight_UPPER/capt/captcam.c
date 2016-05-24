/*
 * Copyright 2013 The Imaging Source Europe GmbH
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include <getopt.h>	/* getopt_long() */

#include <fcntl.h>	/* low-level i/o */
#include <unistd.h>
#include <errno.h>
#include <malloc.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/mman.h>
#include <sys/ioctl.h>

#include <asm/types.h>	/* for videodev2.h */

#include <linux/videodev2.h>

#include <png.h>
#include <zlib.h>

#define CLEAR(x) memset(&(x), 0, sizeof(x))

typedef struct{
	void *start;
	size_t length;
}buffer;
static buffer *buffers = NULL;
static size_t nbuffers = 0;

static size_t width = 0;
static size_t height = 0;
static size_t bytesperline = 0;
//static size_t imageCount = 0;

static char *dev_name = NULL;
static int fd = -1;

static char *imageName = NULL;

static void errno_exit(const char *s){
	fprintf(stderr, "%s error %d, %s\n", s, errno, strerror(errno));
	
	exit(EXIT_FAILURE);
}

static int xioctl(int fd, int request, void *arg){
	int r;
	
	do{
		r = ioctl(fd, request, arg);
	}while(-1 == r && EINTR == errno);
	
	return r;
}

static void process_image(buffer buf){
	/*	const size_t size = 128;
	 char name[size];
	 snprintf(name, size, "images/test%d.png", imageCount);
	 imageCount++;*/
	if(!imageName){
		return;
	}
	FILE *file = fopen(imageName, "wb");
	if(!file){
		errno_exit("Failed to open file!");
		return;
	}
	
	png_structp image = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
	if(!image){
		fclose(file);
		errno_exit("Failed to create write struct!");
		return;
	}
	
	png_infop info = png_create_info_struct(image);
	if(!info){
		png_destroy_write_struct(&image, NULL);
		fclose(file);
		errno_exit("Failed to create info struct!");
		return;
	}
	
	if(setjmp(png_jmpbuf(image))){
		png_destroy_write_struct(&image, &info);
		fclose(file);
		errno_exit("Failed on something!");
		return;
	}
	
	png_init_io(image, file);
	png_set_compression_level(image, Z_BEST_SPEED);
	
	png_set_IHDR(image, info, width, height, 12, PNG_COLOR_TYPE_GRAY, PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_DEFAULT, PNG_FILTER_TYPE_DEFAULT);
	//png_set_gAMA(image, info, 1.0); //gamma!
	// If everything breaks it was Bekah's fault.  Change the 12 above back to 8
	
	png_byte **rows = NULL;
	
	rows = (png_byte **)png_malloc(image, height*sizeof(png_byte *));
	for(size_t i = 0; i < height; i++){
		rows[i] = (png_byte *)png_malloc(image, bytesperline*sizeof(png_byte));
		for(size_t j = 0; j < width; j++){
			rows[i][j] = ((png_byte *)buf.start)[i*width+j];
		}
	}
	
	png_set_rows(image, info, rows);
	
	png_write_png(image, info, PNG_TRANSFORM_IDENTITY, NULL);
	
	for(size_t i = 0; i < height; i++){
		png_free(image, rows[i]);
	}
	png_free(image, rows);
	
 	png_destroy_write_struct(&image, &info);
	fclose(file);
	printf("Wrote File!\n");
}

static void list_framerates(__u32 pixelformat, int width, int height){
	struct v4l2_frmivalenum frmival;
	
	frmival.pixel_format = pixelformat;
	frmival.width = width;
	frmival.height = height;
	
	for(frmival.index = 0; xioctl(fd, VIDIOC_ENUM_FRAMEINTERVALS, &frmival) >= 0; frmival.index++){
		if(frmival.type == V4L2_FRMIVAL_TYPE_DISCRETE){
			fprintf(stdout, "Numerator: %d, Denominator: %d, Frame Rate: %f\n", frmival.discrete.numerator, frmival.discrete.denominator, 1/((double)frmival.discrete.numerator / (double)frmival.discrete.denominator));
		}else{
			fprintf(stdout, "Frame rate range:\n");
			fprintf(stdout, " Min:\n");
			fprintf(stdout, "\tNumerator: %d, Denominator: %d, Frame Rate: %f\n", frmival.stepwise.min.numerator, frmival.stepwise.min.denominator, 1/((double)frmival.stepwise.min.numerator / (double)frmival.stepwise.min.denominator));
			fprintf(stdout, " Max:\n");
			fprintf(stdout, "\tNumerator: %d, Denominator: %d, Frame Rate: %f\n", frmival.stepwise.max.numerator, frmival.stepwise.max.denominator, 1/((double)frmival.stepwise.max.numerator / (double)frmival.stepwise.max.denominator));
		}
	}
}

static void set_framerate(int numerator, int denominator){
	struct v4l2_streamparm parm;
	
	fprintf(stdout, "Set Framerate: %f FPS\n", 1/((double)numerator / (double)denominator));
	
	parm.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
	parm.parm.capture.timeperframe.numerator = numerator;
	parm.parm.capture.timeperframe.denominator = denominator;
	
	if(xioctl(fd, VIDIOC_S_PARM, &parm) < 0){
		fprintf(stderr, "Failed to set frame rate\n");
	}
}

static int read_frame(void){
	struct v4l2_buffer buf;
	unsigned int i;
	
	CLEAR(buf);
	
	buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
	buf.memory = V4L2_MEMORY_MMAP;
	
	if (-1 == xioctl(fd, VIDIOC_DQBUF, &buf)) {
		switch (errno) {
			case EAGAIN:
				return 0;
			case EIO:
				//Could ignore EIO, see spec.
				//fall through
			default:
				errno_exit("VIDIOC_DQBUF");
		}
	}
	
	assert(buf.index < nbuffers);
	
	process_image(buffers[buf.index]);
	
	if(-1 == xioctl(fd, VIDIOC_QBUF, &buf)){
		errno_exit("VIDIOC_QBUF");
	}
	
	return 1;
}

static void mainloop(){
	while(1){
		fd_set fds;
		struct timeval tv;
		int r;
		
		FD_ZERO(&fds);
		FD_SET(fd, &fds);
		
		/* Timeout. */
		tv.tv_sec = 2;
		tv.tv_usec = 0;
		
		r = select(fd + 1, &fds, NULL, NULL, &tv);
		
		if(-1 == r){
			if(EINTR == errno){
				continue;
			}
			
			errno_exit("select");
		}
		
		if(0 == r){
			fprintf(stderr, "select timeout\n");
			exit(EXIT_FAILURE);
		}
		
		if(read_frame()){
			break;
		}
		
		/* EAGAIN - continue select loop. */
	}
}

static void stop_capturing(void){
	enum v4l2_buf_type type;
	type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
	
	if(-1 == xioctl(fd, VIDIOC_STREAMOFF, &type)){
		errno_exit("VIDIOC_STREAMOFF");
	}
}

static void start_capturing(void){
	unsigned int i;
	enum v4l2_buf_type type;
	for(i = 0; i < nbuffers; i++){
		struct v4l2_buffer buf;
		
		CLEAR(buf);
		
		buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
		buf.memory = V4L2_MEMORY_MMAP;
		buf.index = i;
		
		if(-1 == xioctl(fd, VIDIOC_QBUF, &buf)){
			errno_exit("VIDIOC_QBUF");
		}
	}
	
	type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
	
	if(-1 == xioctl(fd, VIDIOC_STREAMON, &type)){
		errno_exit("VIDIOC_STREAMON");
	}
}

static void uninit_device(void){
	for(int i = 0; i < nbuffers; ++i){
		if(-1 == munmap(buffers[i].start, buffers[i].length)){
			errno_exit("munmap");
		}
	}
	free(buffers);
	//free(buf.start);
}

/*static void init_read(unsigned int buffer_size){
 buf.length = buffer_size;
 buf.start = malloc(buffer_size);
 
 if(!buf.start){
 fprintf(stderr, "Out of memory\n");
 exit(EXIT_FAILURE);
 }
 }*/

static void init_mmap(void){
	struct v4l2_requestbuffers req;
	
	CLEAR(req);
	
	req.count = 4;
	req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
	req.memory = V4L2_MEMORY_MMAP;
	
	if(-1 == xioctl(fd, VIDIOC_REQBUFS, &req)){
		if (EINVAL == errno){
			fprintf(stderr, "%s does not support memory mapping\n", dev_name);
			exit(EXIT_FAILURE);
		}else{
			errno_exit("VIDIOC_REQBUFS");
		}
	}
	
	if(req.count < 2){
		fprintf(stderr, "Insufficient buffer memory on %s\n", dev_name);
		exit(EXIT_FAILURE);
	}
	
	buffers = calloc(req.count, sizeof(*buffers));
	
	if(!buffers){
		fprintf(stderr, "Out of memory\n");
		exit(EXIT_FAILURE);
	}
	
	for(nbuffers = 0; nbuffers < req.count; ++nbuffers){
		struct v4l2_buffer buf;
		
		CLEAR(buf);
		
		buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
		buf.memory = V4L2_MEMORY_MMAP;
		buf.index = nbuffers;
		
		if(-1 == xioctl(fd, VIDIOC_QUERYBUF, &buf)){
			errno_exit("VIDIOC_QUERYBUF");
		}
		buffers[nbuffers].length = buf.length;
		buffers[nbuffers].start = mmap(NULL /* start anywhere */, buf.length, PROT_READ | PROT_WRITE /* required */, MAP_SHARED /* recommended */, fd, buf.m.offset);
		
		if(MAP_FAILED == buffers[nbuffers].start){
			errno_exit("mmap");
		}
	}
}

static void init_device(){
	struct v4l2_capability cap;
	struct v4l2_cropcap cropcap;
	struct v4l2_crop crop;
	struct v4l2_format fmt;
	unsigned int min;
	
	if(-1 == xioctl(fd, VIDIOC_QUERYCAP, &cap)){
		if(EINVAL == errno){
			fprintf(stderr, "%s is no V4L2 device\n", dev_name);
			exit(EXIT_FAILURE);
		}else{
			errno_exit("VIDIOC_QUERYCAP");
		}
	}
	
	printf("Card: %s\n", cap.card);
	
	if(!(cap.capabilities & V4L2_CAP_VIDEO_CAPTURE)){
		fprintf(stderr, "%s is no video capture device\n", dev_name);
		exit(EXIT_FAILURE);
	}
	
	/*if(!(cap.capabilities & V4L2_CAP_READWRITE)){
	 fprintf(stderr, "%s does not support read i/o\n", dev_name);
	 exit(EXIT_FAILURE);
	 }*/
	
	if(!(cap.capabilities & V4L2_CAP_STREAMING)){
		fprintf(stderr, "%s does not support streaming i/o\n", dev_name);
		exit(EXIT_FAILURE);
	}
	
	/* Select video input, video standard and tune here. */
	CLEAR(cropcap);
	
	cropcap.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
	
	if(0 == xioctl(fd, VIDIOC_CROPCAP, &cropcap)){
		crop.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
		crop.c = cropcap.defrect; /* reset to default */
		
		if(-1 == xioctl(fd, VIDIOC_S_CROP, &crop)){
			switch(errno){
				case EINVAL:
					/* Cropping not supported. */
					break;
				default:
					/* Errors ignored. */
					break;
			}
		}
	}else{
		/* Errors ignored. */
	}
	
	CLEAR(fmt);
	
	fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
	fmt.fmt.pix.width = 2592;
	fmt.fmt.pix.height = 1944;
	fmt.fmt.pix.pixelformat = V4L2_PIX_FMT_Y16 ;
	fmt.fmt.pix.field = V4L2_FIELD_NONE;
	
	if(-1 == xioctl(fd, VIDIOC_S_FMT, &fmt)){
		errno_exit("VIDIOC_S_FMT");
	}
	
	/* Note VIDIOC_S_FMT may change width and height. */
	
	/* Buggy driver paranoia. */
	min = fmt.fmt.pix.width;
	if(fmt.fmt.pix.bytesperline < min){
		fmt.fmt.pix.bytesperline = min;
	}
	min = fmt.fmt.pix.bytesperline * fmt.fmt.pix.height;
	if(fmt.fmt.pix.sizeimage < min){
		fmt.fmt.pix.sizeimage = min;
	}
	
	width = fmt.fmt.pix.width;
	height = fmt.fmt.pix.height;
	bytesperline = fmt.fmt.pix.bytesperline;
	
	//init_read(fmt.fmt.pix.sizeimage);
	init_mmap();
	
	// Set frame rate to 12 FPS
	set_framerate(1, 12);
}

static void close_device(){
	if(-1 == close(fd)){
		errno_exit("close");
	}
	fd = -1;
}

static void open_device(){
	struct stat st;
	
	if(-1 == stat(dev_name, &st)){
		fprintf(stderr, "Cannot identify '%s': %d, %s\n", dev_name, errno, strerror(errno));
		exit(EXIT_FAILURE);
	}
	
	if(!S_ISCHR(st.st_mode)){
		fprintf(stderr, "%s is no device\n", dev_name);
		exit(EXIT_FAILURE);
	}
	
	fd = open(dev_name, O_RDWR /* required */ | O_NONBLOCK, 0);
	
	if(-1 == fd){
		fprintf(stderr, "Cannot open '%s': %d, %s\n", dev_name, errno, strerror(errno));
		exit(EXIT_FAILURE);
	}
}

static void list_format_info(void){
	struct v4l2_fmtdesc fmtdesc;
	struct v4l2_frmsizeenum frms;
	
	fmtdesc.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
	
	for(fmtdesc.index = 0; !xioctl(fd, VIDIOC_ENUM_FMT, &fmtdesc); fmtdesc.index++){
		fprintf(stdout, "Format %d: %s\n", fmtdesc.index, fmtdesc.description );
		fprintf(stdout, " Size:\n");
		frms.pixel_format = fmtdesc.pixelformat;
		for(frms.index = 0; ! xioctl (fd, VIDIOC_ENUM_FRAMESIZES, &frms); frms.index++){
			if(frms.type == V4L2_FRMSIZE_TYPE_DISCRETE){
				fprintf(stdout, " %dx%d\n", frms.discrete.width, frms.discrete.height);
				fprintf(stdout, "----- Frame Rates -----\n");
				list_framerates(fmtdesc.pixelformat, frms.discrete.width, frms.discrete.height);
			}else{
				fprintf(stdout, " Range\n");
				fprintf(stdout, "\tMin:\n");
				fprintf(stdout, "\t\tWidth: %d, Height: %d\n", frms.stepwise.min_width, frms.stepwise.min_height);
				fprintf(stdout, "\tMax:\n");
				fprintf(stdout, "\t\tWidth: %d, Height: %d\n", frms.stepwise.max_width, frms.stepwise.max_height);
				fprintf(stdout, "----- Frame Rates -----\n");
				fprintf(stdout, "\tMin:\n");
				list_framerates(fmtdesc.pixelformat, frms.stepwise.min_width, frms.stepwise.min_height);
				fprintf(stdout, "\tMax:\n");
				list_framerates(fmtdesc.pixelformat, frms.stepwise.max_width, frms.stepwise.max_height);
			}
		}
	}
}

static void getControl(int *input, int ctl){
	struct v4l2_queryctrl queryctrl;
	memset(&queryctrl, 0, sizeof(queryctrl));
	queryctrl.id = ctl;
	
	if(-1 == xioctl(fd, VIDIOC_QUERYCTRL, &queryctrl)){
		if(errno != EINVAL){
			perror("VIDIOC_QUERYCTRL");
			exit(EXIT_FAILURE);
		}else{
			printf("This command is not supported.\n");
		}
	}else if(queryctrl.flags & V4L2_CTRL_FLAG_DISABLED){
		printf ("This command is disabled.\n");
	}else{
		struct v4l2_control control;
		memset(&control, 0, sizeof(control));
		
		control.id = ctl;
		
		if(-1 == xioctl(fd, VIDIOC_G_CTRL, &control)){
			perror("VIDIOC_S_CTRL");
			exit(EXIT_FAILURE);
		}
		
		*input = control.value;
	}
}

static void setControl(int input, int ctl){
	struct v4l2_queryctrl queryctrl;
	memset(&queryctrl, 0, sizeof(queryctrl));
	queryctrl.id = ctl;
	
	if(-1 == xioctl(fd, VIDIOC_QUERYCTRL, &queryctrl)){
		if(errno != EINVAL){
			perror("VIDIOC_QUERYCTRL");
			exit(EXIT_FAILURE);
		}else{
			printf("This command is not supported.\n");
		}
	}else if(queryctrl.flags & V4L2_CTRL_FLAG_DISABLED){
		printf ("This command is disabled.\n");
	}else{
		struct v4l2_control control;
		memset(&control, 0, sizeof(control));
		
		control.id = ctl;
		control.value = input;
		
		if(-1 == xioctl(fd, VIDIOC_S_CTRL, &control)){
			perror("VIDIOC_S_CTRL");
			exit(EXIT_FAILURE);
		}
	}
}

static void usage(FILE *fp, int argc, char **argv){
	fprintf(fp,
					"Usage: %s [options]\n\n"
					"Options:\n"
					"-d | --device name		Video device name [/dev/video0]\n"
					"-h | --help			Print this message\n"
					"-l						List available video formats and exit\n"
					"-g | --gamma gamma		Adjust gamma and exit\n"
					"-i | --gain gain		Adjust gain and exit\n"
					"-e | --exp exp			Adjust exposure and exit\n"
					"-a | --auto val		Adjust auto_exposure and exit\n"
					"-o | --out file		Output image to file [img.png]\n"
					"-t | --test			Open device and issue one read command but don't write output\n"
					"",
					argv[0]);
}

static const char short_options[] = "d:hlg:i:e:a:o:t";

static const struct option long_options[] = {
	{ "device",	required_argument,	NULL,		'd' },
	{ "help",	no_argument,		NULL,		'h' },
	{ "gamma",	required_argument,	NULL,		'g' },
	{ "gain",	required_argument,	NULL,		'i' },
	{ "exp",	required_argument,	NULL,		'e' },
	{ "auto",	required_argument,	NULL,		'a' },
	{ "out",	required_argument,	NULL,		'o' },
	{ "test",	no_argument,	NULL,		't' },
	{ 0, 0, 0, 0 }
};

int main(int argc, char **argv){
	int do_list_formats = 0;
	dev_name = "/dev/video0";
	int input = 100;
	int command = V4L2_CID_GAMMA;
	int doCommand = 0;
	imageName = "img.png";
	
	while(1){
		int index;
		int c;
		
		c = getopt_long(argc, argv, short_options, long_options, &index);
		
		if(-1 == c){
			break;
		}
		
		switch(c){
			case 0: /* getopt_long() flag */
				break;
			case 'd':
				dev_name = optarg;
				break;
			case 'h':
				usage(stdout, argc, argv);
				exit(EXIT_SUCCESS);
			case 'l':
				do_list_formats = 1;
				break;
			case 'a':
				command = V4L2_CID_EXPOSURE_AUTO;
				input = atoi(optarg);
				doCommand = 1;
				break;
			case 'e':
				command = V4L2_CID_EXPOSURE_ABSOLUTE;
				input = atoi(optarg);
				doCommand = 1;
				break;
			case 'i':
				command = V4L2_CID_GAIN;
				input = atoi(optarg);
				doCommand = 1;
				break;
			case 'g':
				command = V4L2_CID_GAMMA;
				input = atoi(optarg);
				doCommand = 1;
				break;
			case 'o':
				imageName = optarg;
				break;
			case 't':
				imageName = NULL;
				break;
			default:
				usage(stderr, argc, argv);
				exit(EXIT_FAILURE);
		}
	}
	
	open_device();
	
	if(doCommand){
		int temp = 0;
		getControl(&temp, command);
		printf("Executing command 0x%X, previous value: %d ", command, temp);
		setControl(input, command);
		getControl(&temp, command);
		printf("current value: %d\n", temp);
		close_device();
		exit(EXIT_SUCCESS);
	}
	
	if(do_list_formats){
		list_format_info();
		close_device();
		exit(EXIT_SUCCESS);
	}
	
	init_device();
	start_capturing();
	mainloop();
	stop_capturing();
	uninit_device();
	
	printf("\n");
	close_device();
	exit(EXIT_SUCCESS);
	
	return 0;
}
