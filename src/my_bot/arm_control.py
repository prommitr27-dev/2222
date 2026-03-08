#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

class ArmController(Node):
    def __init__(self):
        super().__init__('arm_controller_node')
        
        # สร้าง Publisher สำหรับส่งคำสั่งไปที่แขน (arm_controller)
        self.arm_pub = self.create_publisher(
            JointTrajectory, 
            '/arm_controller/joint_trajectory', 
            10)
            
        # สร้าง Publisher สำหรับส่งคำสั่งไปที่ตัวคีบ (gripper_controller)
        self.gripper_pub = self.create_publisher(
            JointTrajectory, 
            '/gripper_controller/joint_trajectory', 
            10)

    def move_arm(self, base, shoulder, forearm):
        msg = JointTrajectory()
        msg.joint_names = ['arm_base_joint', 'shoulder_joint', 'forearm_joint']
        
        point = JointTrajectoryPoint()
        point.positions = [float(base), float(shoulder), float(forearm)]
        # ใช้เวลา 2 วินาทีในการเคลื่อนที่ไปจุดนั้น
        point.time_from_start = Duration(sec=2, nanosec=0) 
        
        msg.points.append(point)
        self.arm_pub.publish(msg)
        self.get_logger().info(f'ขยับแขนไปที่: [{base}, {shoulder}, {forearm}]')

    def move_gripper(self, left, right):
        msg = JointTrajectory()
        msg.joint_names = ['left_finger_joint', 'right_finger_joint']
        
        point = JointTrajectoryPoint()
        point.positions = [float(left), float(right)]
        # ใช้เวลา 1 วินาทีในการบีบ/อ้า
        point.time_from_start = Duration(sec=1, nanosec=0)
        
        msg.points.append(point)
        self.gripper_pub.publish(msg)
        self.get_logger().info(f'สั่งมือคีบ: [{left}, {right}]')

def main(args=None):
    rclpy.init(args=args)
    node = ArmController()
    
    print("\n--- ระบบควบคุมแขนหุ่นยนต์พร้อมทำงาน! ---")
    print("คำสั่งแขน (พิมพ์ 3 ตัวเลข): [base] [shoulder] [forearm]")
    print("คำสั่งมือคีบ (พิมพ์ 2 ตัวเลข): [left_finger] [right_finger]")
    print("พิมพ์ 'q' เพื่อออก\n")

    try:
        while rclpy.ok():
            user_input = input("ป้อนคำสั่ง (เช่น '0 0.5 -0.5' หรือ '0.04 -0.04'): ")
            
            if user_input.lower() == 'q':
                break
                
            values = user_input.split()
            
            if len(values) == 3:
                node.move_arm(values[0], values[1], values[2])
            elif len(values) == 2:
                node.move_gripper(values[0], values[1])
            else:
                print("รูปแบบผิด! กรุณาใส่ตัวเลข 3 ตัว (สำหรับแขน) หรือ 2 ตัว (สำหรับนิ้ว)")
                
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
