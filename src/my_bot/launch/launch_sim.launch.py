import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    package_name='my_bot'
    
    world_file_path = os.path.join(
        get_package_share_directory(package_name),
        'worlds',
        '211_fixed.world'
    )
    
    rsp = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory(package_name),'launch','rsp.launch.py'
                )]), launch_arguments={'use_sim_time': 'true'}.items()
    )
    
    gazebo = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')]),
                launch_arguments={'world': world_file_path}.items()
             )
             
    spawn_entity = Node(package='gazebo_ros', executable='spawn_entity.py',
                        arguments=['-topic', 'robot_description',
                                   '-entity', 'my_bot',
                                   '-x', '4.374614',
                                   '-y', '-4.186749',
                                   '-z', '0.2',
                                   '-Y', '1.572549'],
                        output='screen')
   
    # 🌟 ลบ Node ของ diff_drive_spawner ออกเรียบร้อยครับ 🌟
    
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster"],
    )
    
    arm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["arm_controller"],
    )

    gripper_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["gripper_controller"],
    )
    # สร้างตัวแปรชี้ไปหาไฟล์ URDF ของกล่อง
    box_urdf_path = os.path.join(
        get_package_share_directory(package_name),
        'urdf',  # สมมติว่าคุณเซฟกล่องไว้ในโฟลเดอร์ urdf
        'box.urdf' # เปลี่ยนชื่อไฟล์ให้ตรงกับที่คุณเซฟ
    )

    # Node สำหรับเสกกล่องตามพิกัดเป๊ะๆ
    spawn_box = Node(
        package='gazebo_ros', 
        executable='spawn_entity.py',
        arguments=[
            '-entity', 'heavy_box',
            '-file', box_urdf_path,
            '-x', '2.743495',
            '-y', '-4.405608',
            '-z', '0.25'
        ],
        output='screen'
    )

    #robot_localization_node = Node(
     #    package='robot_localization',
      #   executable='ekf_node',
      #   name='ekf_filter_node',
      #   output='screen',
      #   parameters=[os.path.join(get_package_share_directory(package_name), 'config', 'ekf.yaml'), {'use_sim_time': True}]
    #)

    return LaunchDescription([
        rsp,
        gazebo,
    	spawn_box,
        spawn_entity,
        joint_state_broadcaster_spawner,
        # 🌟 ลบ diff_drive_spawner ออกจากรายการรันตรงนี้ด้วยครับ 🌟
        arm_controller_spawner,
        gripper_controller_spawner,
        #robot_localization_node
    ])
