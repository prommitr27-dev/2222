#!/usr/bin/env python3
import rclpy
from linkattacher_msgs.srv import AttachLink, DetachLink
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
from std_srvs.srv import Empty
import sys, select, termios, tty, threading, math, time

msg = """
======================================
🎮 ระบบควบคุมด้วยมือ (Full Manual Control)
======================================
ขับเคลื่อนล้อ:
        w
   a    s    d
        x

  w/x : เดินหน้า / ถอยหลัง
  a/d : เลี้ยวซ้าย / เลี้ยวขวา
  s   : หยุดทันที + ปิด BRAKE

  q/z : เพิ่ม/ลด ทั้ง linear และ angular speed
  e/c : เพิ่ม/ลด เฉพาะ linear speed
  r/v : เพิ่ม/ลด เฉพาะ angular speed

  b   : 🔴 BRAKE toggle — ล็อคตำแหน่ง (smart slope hold)
        กด b ขณะหยุดอยู่บนทางลาด
        ระบบจะจำตำแหน่ง XY แล้วดันกลับอัตโนมัติถ้าไหล

  n   : 🔵 SLOPE DOWN mode — ลงเนินช้าๆ ควบคุมได้ (กด n อีกครั้งเพื่อปิด)

ควบคุมแขนกล:
  u / j : หมุนฐาน (Base) ซ้าย/ขวา
  i / k : ยกไหล่ (Shoulder) ขึ้น/ลง
  o / l : งอศอก (Forearm) ขึ้น/ลง

  t   : 🤖 TUCK arm tight to body (use before slope)
  y   : 🦾 UNTUCK arm back to grab position

  -   : attach box
  =   : detach box
  ]   : อ้าออกสุด

กด CTRL-C เพื่อออก
======================================
"""

MOVE_BINDINGS = {
    'w': ( 1,  0),
    'x': (-1,  0),
    'a': ( 0,  1),
    'd': ( 0, -1),
}

SPEED_BINDINGS = {
    'q': (1.1, 1.1),
    'z': (0.9, 0.9),
    'e': (1.1, 1.0),
    'c': (0.9, 1.0),
    'r': (1.0, 1.1),
    'v': (1.0, 0.9),
}

CORRECTION_GAIN = 6.0
MAX_CORRECTION = 0.8
DRIFT_DEADBAND = 0.02


class FullTeleopNode(Node):
    def __init__(self):
        super().__init__('full_teleop_node')
        self.vel_pub  = self.create_publisher(Twist, '/cmd_vel', 10)
        self.arm_pub  = self.create_publisher(JointTrajectory, '/arm_controller/joint_trajectory', 10)
        self.grip_pub = self.create_publisher(JointTrajectory, '/gripper_controller/joint_trajectory', 10)

        self.grip_pos  = 0.0
        self.grip_step = 0.01
        self.arm_pos   = [0.0, 0.0, 0.0]
        self.arm_step  = 0.05

        self.linear_speed  = 0.5
        self.angular_speed = 1.0

        self.current_x   = 0.0
        self.current_y   = 0.0
        self.current_yaw = 0.0

        self.brake_on = False
        self.brake_hold_x = 0.0
        self.brake_hold_y = 0.0
        self.slope_down = False
        self.slope_down_angular = 0.0

        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self._odom_callback, 10)

        self.brake_timer = self.create_timer(0.02, self._brake_callback)

        self.attach_cli = self.create_client(AttachLink, '/ATTACHLINK')
        self.detach_cli = self.create_client(DetachLink, '/DETACHLINK')
        self.pause_cli = self.create_client(Empty, '/pause_physics')
        self.unpause_cli = self.create_client(Empty, '/unpause_physics')

    def _odom_callback(self, msg):
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        self.current_yaw = math.atan2(siny, cosy)

    def _brake_callback(self):
        if self.slope_down:
            self.send_vel(0.12, self.slope_down_angular)
            return

        if not self.brake_on:
            return

        dx = self.brake_hold_x - self.current_x
        dy = self.brake_hold_y - self.current_y
        drift = math.sqrt(dx * dx + dy * dy)

        if drift < DRIFT_DEADBAND:
            self.send_vel(0.0, 0.0)
            return

        forward_correction = (
            dx * math.cos(self.current_yaw) +
            dy * math.sin(self.current_yaw)
        )

        correction_vel = CORRECTION_GAIN * forward_correction
        correction_vel = max(-MAX_CORRECTION, min(MAX_CORRECTION, correction_vel))
        self.send_vel(correction_vel, 0.0)

    def toggle_slope_down(self):
        self.slope_down = not self.slope_down
        if self.slope_down:
            self.brake_on = False
            print('\n🔵 SLOPE DOWN ON  — ลงเนินช้าๆ อัตโนมัติ')
        else:
            self.send_vel(0.0, 0.0)
            print('\n⚪ SLOPE DOWN OFF')

    def toggle_brake(self):
        self.brake_on = not self.brake_on
        if self.brake_on:
            self.brake_hold_x = self.current_x
            self.brake_hold_y = self.current_y
            self.send_vel(0.0, 0.0)
            print(f'\n🔴 BRAKE ON  — ล็อคที่ x={self.brake_hold_x:.3f}, y={self.brake_hold_y:.3f}')
            print('   แขนกลยังใช้งานได้ตามปกติ')
        else:
            print('\n🟢 BRAKE OFF — หุ่นพร้อมเคลื่อนที่')

    def send_vel(self, linear, angular):
        t = Twist()
        t.linear.x = float(linear)
        t.angular.z = float(angular)
        self.vel_pub.publish(t)

    def send_arm(self):
        jt = JointTrajectory()
        jt.joint_names = ['arm_base_joint', 'shoulder_joint', 'forearm_joint']
        pt = JointTrajectoryPoint()
        pt.positions = self.arm_pos
        pt.time_from_start = Duration(sec=0, nanosec=100000000)
        jt.points.append(pt)
        self.arm_pub.publish(jt)

    def send_grip(self):
        jt = JointTrajectory()
        jt.joint_names = ['left_finger_joint', 'right_finger_joint']
        pt = JointTrajectoryPoint()
        pt.positions = [-self.grip_pos, self.grip_pos]
        pt.time_from_start = Duration(sec=0, nanosec=100000000)
        jt.points.append(pt)
        self.grip_pub.publish(jt)

    def tuck_arm(self):
        target = [0.0, 0.0, 0.25]
        steps = 20
        for i in range(1, steps + 1):
            for j in range(3):
                self.arm_pos[j] += (target[j] - self.arm_pos[j]) * (1.0 / (steps - i + 1))
            self.send_arm()
            time.sleep(0.1)
        print('\n🤖 ARM TUCKED — safe to drive slope')

    def untuck_arm(self):
        target = [0.0, 0.0, 0.0]
        steps = 20
        for i in range(1, steps + 1):
            for j in range(3):
                self.arm_pos[j] += (target[j] - self.arm_pos[j]) * (1.0 / (steps - i + 1))
            self.send_arm()
            time.sleep(0.1)
        print('\n🦾 ARM UNTUCKED')

    def attach_box(self):
        print("attach_box called")

        if not self.attach_cli.wait_for_service(timeout_sec=1.0):
            print("Service /ATTACHLINK not available")
            return

        if self.pause_cli.service_is_ready():
            self.pause_cli.call_async(Empty.Request())
            time.sleep(0.1)

        req = AttachLink.Request()
        req.model1_name = 'my_bot'
        req.link1_name  = 'forearm_link'
        req.model2_name = 'heavy_box'
        req.link2_name  = 'box_link'

        print("Sending attach request:", req)
        future = self.attach_cli.call_async(req)
        future.add_done_callback(self._attach_done)

        time.sleep(0.2)

        if self.unpause_cli.service_is_ready():
            self.unpause_cli.call_async(Empty.Request())

    def detach_box(self):
        print("detach_box called")

        if not self.detach_cli.wait_for_service(timeout_sec=1.0):
            print("Service /DETACHLINK not available")
            return

        req = DetachLink.Request()
        req.model1_name = 'my_bot'
        req.link1_name  = 'forearm_link'
        req.model2_name = 'heavy_box'
        req.link2_name  = 'box_link'

        print("Sending detach request:", req)
        future = self.detach_cli.call_async(req)
        future.add_done_callback(self._detach_done)

    def _attach_done(self, future):
        try:
            print("Attach result:", future.result())
        except Exception as e:
            print("Attach failed:", e)

    def _detach_done(self, future):
        try:
            print("Detach result:", future.result())
        except Exception as e:
            print("Detach failed:", e)


def get_key(settings):
    tty.setraw(sys.stdin.fileno())
    rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
    key = sys.stdin.read(1) if rlist else ''
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


def main():
    settings = termios.tcgetattr(sys.stdin)
    rclpy.init()
    node = FullTeleopNode()

    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    print(msg)
    print(f'Speed: linear={node.linear_speed:.2f}  angular={node.angular_speed:.2f}')

    try:
        while rclpy.ok():
            key = get_key(settings)

            if key == '\x03':
                break

            if key == 'b':
                node.toggle_brake()

            elif key == 'n':
                node.toggle_slope_down()

            elif key == '':
                if node.slope_down:
                    node.slope_down_angular = 0.0

            elif key in MOVE_BINDINGS:
                lin_dir, ang_dir = MOVE_BINDINGS[key]
                if node.slope_down:
                    if ang_dir != 0:
                        node.slope_down_angular = ang_dir * node.angular_speed
                    else:
                        node.slope_down = False
                        node.slope_down_angular = 0.0
                        print('\n⚪ SLOPE DOWN OFF — manual control')
                        node.send_vel(lin_dir * node.linear_speed, 0.0)
                elif node.brake_on:
                    print('⚠️  ปิด BRAKE ก่อน (กด b)', end='\r')
                else:
                    node.send_vel(
                        lin_dir * node.linear_speed,
                        ang_dir * node.angular_speed
                    )

            elif key == 's':
                node.brake_on = False
                node.send_vel(0.0, 0.0)
                print('\n🟢 BRAKE OFF — stopped')

            elif key in SPEED_BINDINGS:
                lin_mul, ang_mul = SPEED_BINDINGS[key]
                node.linear_speed *= lin_mul
                node.angular_speed *= ang_mul
                print(f'Speed: linear={node.linear_speed:.2f}  angular={node.angular_speed:.2f}')

            elif key == 'u':
                node.arm_pos[0] += node.arm_step
                node.send_arm()
            elif key == 'j':
                node.arm_pos[0] -= node.arm_step
                node.send_arm()
            elif key == 'i':
                node.arm_pos[1] -= node.arm_step
                node.send_arm()
            elif key == 'k':
                node.arm_pos[1] += node.arm_step
                node.send_arm()
            elif key == 'o':
                node.arm_pos[2] -= node.arm_step
                node.send_arm()
            elif key == 'l':
                node.arm_pos[2] += node.arm_step
                node.send_arm()

            elif key == 't':
                node.tuck_arm()
            elif key == 'y':
                node.untuck_arm()

            elif key == '[':
                node.grip_pos = min(0.045, node.grip_pos + node.grip_step)
                node.send_grip()
            elif key == ']':
                node.grip_pos = max(-0.05, node.grip_pos - node.grip_step)
                node.send_grip()

            elif key == '-':
                node.attach_box()
            elif key == '=':
                node.detach_box()

    except Exception as e:
        print(e)
    finally:
        node.brake_on = False
        node.send_vel(0.0, 0.0)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
