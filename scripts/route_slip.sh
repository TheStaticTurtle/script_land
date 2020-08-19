slattach -p slip -s 9600 -L /dev/ttyACM0 &
ifconfig sl0 192.169.55.1 pointopoint 192.169.55.2 up
/sbin/route add default dev sl0 &
echo 1 > /proc/sys/net/ipv4/ip_forward

echo "SLIP Configured pinging now"
echo "Ensure that you run \"sudo killall -9 slattach\" while exiting"
ping -i 4 192.169.55.2

sudo killall -9 slattach

#/sbin/slattach -p slip -s 115200 -L /dev/ttyACM0 &
#sudo ifconfig sl0 192.169.55.2 pointopoint 192.169.55.1 up
#/sbin/route add default dev sl0 &s