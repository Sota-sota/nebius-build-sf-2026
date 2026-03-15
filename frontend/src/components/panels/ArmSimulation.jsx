import { useRef, useMemo } from "react"
import { Canvas, useFrame } from "@react-three/fiber"
import { OrbitControls, ContactShadows } from "@react-three/drei"
import { useAppStore } from "../../stores/appStore"

// --- SO-101 accurate dimensions (scaled for display, proportional to real arm) ---
// Real arm: ~111mm wide x 532mm tall
// Scale: 1 unit ≈ 10cm

// Colors matching real SO-101 follower
const WHITE_PLA = "#f0ece4"       // off-white PLA printed body
const SERVO_BLUE = "#2563eb"      // STS3215 servo motor casing (Feetech blue)
const SERVO_DARK = "#1e3a5f"      // servo label/detail side
const METAL_SILVER = "#c0c0c0"    // metal screws, horn
const CLAMP_GRAY = "#888888"      // table clamp
const ACCENT_RING = "#60a5fa"     // status accent

// Segment lengths (proportional to real SO-101)
const BASE_H = 0.35              // base holder height
const UPPER_ARM = 1.1            // shoulder to elbow
const FOREARM = 0.95             // elbow to wrist
const WRIST_H = 0.35             // wrist flex section
const GRIPPER_BASE_H = 0.15
const FINGER_LEN = 0.28

// Servo box dimensions (STS3215 is ~40x20x40mm → scaled)
const SERVO_W = 0.24
const SERVO_H = 0.40
const SERVO_D = 0.20

const POSITION_3D = {
  "far-left":     [-2.0, 0, 0],
  "center-left":  [-1.0, 0, 0],
  "center":       [0.0, 0, 0.8],
  "center-right": [1.0, 0, 0],
  "far-right":    [2.0, 0, 0],
}

const COLOR_MAP = {
  red: "#ef4444", blue: "#3b82f6", green: "#22c55e", yellow: "#eab308",
  orange: "#f97316", purple: "#a855f7", pink: "#ec4899", white: "#e4e4e7",
  black: "#3f3f46", brown: "#92400e", silver: "#d4d4d8", gray: "#a1a1aa",
}

const SIZE_SCALE = { tiny: 0.08, small: 0.12, medium: 0.18, large: 0.25 }

const MOCK_OBJECTS = [
  { id: "mock_1", name: "Red Mug", position: "center-left", estimated_size: "medium", color: "red", material_guess: "ceramic", graspable: true, confidence: 0.92 },
  { id: "mock_2", name: "Green Apple", position: "center-right", estimated_size: "small", color: "green", material_guess: "organic", graspable: true, confidence: 0.88 },
  { id: "mock_3", name: "Blue Pen", position: "far-right", estimated_size: "tiny", color: "blue", material_guess: "plastic", graspable: true, confidence: 0.95 },
]

function lerp(a, b, t) {
  return a + (b - a) * t * 0.08
}

// STS3215 servo motor box — the blue rectangular servo visible at each joint
function ServoMotor({ rotation = [0, 0, 0] }) {
  return (
    <group rotation={rotation}>
      <mesh>
        <boxGeometry args={[SERVO_W, SERVO_H, SERVO_D]} />
        <meshStandardMaterial color={SERVO_BLUE} metalness={0.4} roughness={0.5} />
      </mesh>
      {/* Servo label stripe */}
      <mesh position={[0, 0, SERVO_D / 2 + 0.001]}>
        <planeGeometry args={[SERVO_W * 0.6, SERVO_H * 0.3]} />
        <meshBasicMaterial color={SERVO_DARK} />
      </mesh>
      {/* Motor horn (output shaft disc) */}
      <mesh position={[0, SERVO_H / 2 + 0.02, 0]}>
        <cylinderGeometry args={[0.06, 0.06, 0.03, 12]} />
        <meshStandardMaterial color={METAL_SILVER} metalness={0.8} roughness={0.2} />
      </mesh>
    </group>
  )
}

// White PLA arm link — the structural bracket connecting joints
function ArmLink({ length, width = 0.12, thickness = 0.06 }) {
  return (
    <mesh position={[0, length / 2, 0]}>
      <boxGeometry args={[width, length, thickness]} />
      <meshStandardMaterial color={WHITE_PLA} metalness={0.05} roughness={0.85} />
    </mesh>
  )
}

// Double-sided arm bracket (two PLA plates on each side of servo)
function ArmBracket({ length, gap = 0.22 }) {
  return (
    <group>
      <mesh position={[0, length / 2, gap / 2]}>
        <boxGeometry args={[0.10, length, 0.04]} />
        <meshStandardMaterial color={WHITE_PLA} metalness={0.05} roughness={0.85} />
      </mesh>
      <mesh position={[0, length / 2, -gap / 2]}>
        <boxGeometry args={[0.10, length, 0.04]} />
        <meshStandardMaterial color={WHITE_PLA} metalness={0.05} roughness={0.85} />
      </mesh>
    </group>
  )
}

// Gripper finger — the SO-101 has a parallel-jaw gripper with flat PLA fingers
function GripperFinger({ side, openAmount }) {
  const spread = side * (0.04 + openAmount * 0.08)
  return (
    <group position={[spread, 0, 0]}>
      {/* Finger plate */}
      <mesh position={[0, FINGER_LEN / 2, 0]}>
        <boxGeometry args={[0.03, FINGER_LEN, 0.06]} />
        <meshStandardMaterial color={WHITE_PLA} metalness={0.05} roughness={0.85} />
      </mesh>
      {/* Finger tip (slightly wider for gripping) */}
      <mesh position={[0, FINGER_LEN, 0]}>
        <boxGeometry args={[0.04, 0.04, 0.07]} />
        <meshStandardMaterial color={WHITE_PLA} metalness={0.05} roughness={0.85} />
      </mesh>
    </group>
  )
}

function SO101Arm() {
  const armStatus = useAppStore((s) => s.armStatus)
  const pipelineStatus = useAppStore((s) => s.pipelineStatus)

  const smoothJoints = useRef([0, 0, 0, 0, 0, 0])
  const shoulderPanRef = useRef()    // J1: base rotation
  const shoulderLiftRef = useRef()   // J2: shoulder lift
  const elbowFlexRef = useRef()      // J3: elbow flex
  const wristFlexRef = useRef()      // J4: wrist flex
  const wristRollRef = useRef()      // J5: wrist roll
  const idlePhase = useRef(0)

  useFrame((state, delta) => {
    const target = armStatus?.joint_positions || [0, 0, 0, 0, 0, 0]
    const isIdle = !armStatus || pipelineStatus === "idle" || pipelineStatus === "completed"

    for (let i = 0; i < 6; i++) {
      smoothJoints.current[i] = lerp(smoothJoints.current[i], target[i], delta)
    }
    const j = smoothJoints.current

    if (isIdle) {
      idlePhase.current += delta * 0.8
      const breath = Math.sin(idlePhase.current) * 0.04
      const sway = Math.sin(idlePhase.current * 0.7) * 0.025
      if (shoulderLiftRef.current) shoulderLiftRef.current.rotation.z = -0.25 + breath
      if (elbowFlexRef.current) elbowFlexRef.current.rotation.z = 0.45 + sway
      if (wristFlexRef.current) wristFlexRef.current.rotation.z = sway * 0.5
    } else {
      if (shoulderLiftRef.current) shoulderLiftRef.current.rotation.z = j[1]
      if (elbowFlexRef.current) elbowFlexRef.current.rotation.z = j[2]
      if (wristFlexRef.current) wristFlexRef.current.rotation.z = j[3]
    }

    if (shoulderPanRef.current) shoulderPanRef.current.rotation.y = j[0]
    if (wristRollRef.current) wristRollRef.current.rotation.y = j[4]
  })

  const gripperVal = armStatus?.joint_positions?.[5] ?? 0
  const openAmount = 1 - Math.min(1, gripperVal)

  const accentColor = useMemo(() => {
    switch (pipelineStatus) {
      case "executing": return "#22c55e"
      case "awaiting_approval": return "#f59e0b"
      case "error": return "#ef4444"
      default: return ACCENT_RING
    }
  }, [pipelineStatus])

  return (
    <group position={[0, -1.5, 0]}>
      {/* === TABLE CLAMP === */}
      {/* Clamp base plate */}
      <mesh position={[0, 0.02, 0]}>
        <boxGeometry args={[0.5, 0.04, 0.4]} />
        <meshStandardMaterial color={CLAMP_GRAY} metalness={0.6} roughness={0.4} />
      </mesh>
      {/* Clamp jaw (under table edge) */}
      <mesh position={[0.2, -0.06, 0]}>
        <boxGeometry args={[0.06, 0.12, 0.25]} />
        <meshStandardMaterial color={CLAMP_GRAY} metalness={0.6} roughness={0.4} />
      </mesh>
      {/* Clamp screw knob */}
      <mesh position={[0.2, -0.14, 0]}>
        <cylinderGeometry args={[0.04, 0.04, 0.03, 8]} />
        <meshStandardMaterial color={METAL_SILVER} metalness={0.8} roughness={0.2} />
      </mesh>

      {/* Status ring on base */}
      <mesh position={[0, 0.05, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.18, 0.22, 32]} />
        <meshStandardMaterial color={accentColor} emissive={accentColor} emissiveIntensity={0.6} transparent opacity={0.7} />
      </mesh>

      {/* === J1: SHOULDER PAN (base rotation) === */}
      <group ref={shoulderPanRef} position={[0, 0.04, 0]}>
        {/* Base motor holder — white PLA housing */}
        <mesh position={[0, BASE_H / 2, 0]}>
          <boxGeometry args={[0.28, BASE_H, 0.28]} />
          <meshStandardMaterial color={WHITE_PLA} metalness={0.05} roughness={0.85} />
        </mesh>
        {/* Motor 1 (shoulder pan) — visible inside base */}
        <group position={[0, 0.08, 0]}>
          <ServoMotor rotation={[0, 0, Math.PI / 2]} />
        </group>

        {/* === J2: SHOULDER LIFT === */}
        <group ref={shoulderLiftRef} position={[0, BASE_H, 0]} rotation={[0, 0, -0.25]}>
          {/* Motor 2 at shoulder joint */}
          <ServoMotor />
          {/* Upper arm brackets (two plates sandwiching servo) */}
          <ArmBracket length={UPPER_ARM} gap={SERVO_D + 0.06} />

          {/* === J3: ELBOW FLEX === */}
          <group ref={elbowFlexRef} position={[0, UPPER_ARM, 0]} rotation={[0, 0, 0.45]}>
            {/* Motor 3 at elbow */}
            <ServoMotor />
            {/* Forearm brackets */}
            <ArmBracket length={FOREARM} gap={SERVO_D + 0.06} />

            {/* === J4: WRIST FLEX === */}
            <group ref={wristFlexRef} position={[0, FOREARM, 0]}>
              {/* Motor holder 4 — white housing around servo */}
              <mesh position={[0, 0.08, 0]}>
                <boxGeometry args={[0.18, 0.16, 0.18]} />
                <meshStandardMaterial color={WHITE_PLA} metalness={0.05} roughness={0.85} />
              </mesh>
              {/* Motor 4 */}
              <group position={[0, 0.08, 0]} scale={[0.8, 0.8, 0.8]}>
                <ServoMotor />
              </group>

              {/* === J5: WRIST ROLL === */}
              <group ref={wristRollRef} position={[0, WRIST_H, 0]}>
                {/* Motor 5 — wrist roll servo */}
                <group scale={[0.7, 0.7, 0.7]}>
                  <ServoMotor rotation={[Math.PI / 2, 0, 0]} />
                </group>
                {/* Wrist housing */}
                <mesh position={[0, 0.06, 0]}>
                  <boxGeometry args={[0.14, 0.12, 0.14]} />
                  <meshStandardMaterial color={WHITE_PLA} metalness={0.05} roughness={0.85} />
                </mesh>

                {/* === GRIPPER === */}
                <group position={[0, 0.12, 0]}>
                  {/* Gripper base plate */}
                  <mesh position={[0, GRIPPER_BASE_H / 2, 0]}>
                    <boxGeometry args={[0.16, GRIPPER_BASE_H, 0.08]} />
                    <meshStandardMaterial color={WHITE_PLA} metalness={0.05} roughness={0.85} />
                  </mesh>
                  {/* Motor 6 — gripper servo (small, inside) */}
                  <group position={[0, 0.04, 0]} scale={[0.6, 0.6, 0.6]}>
                    <ServoMotor />
                  </group>
                  {/* Parallel jaw fingers */}
                  <group position={[0, GRIPPER_BASE_H, 0]}>
                    <GripperFinger side={1} openAmount={openAmount} />
                    <GripperFinger side={-1} openAmount={openAmount} />
                  </group>
                </group>
              </group>
            </group>
          </group>
        </group>
      </group>
    </group>
  )
}

function getShape(name) {
  const n = (name || "").toLowerCase()
  if (n.includes("mug") || n.includes("cup") || n.includes("can") || n.includes("bottle")) return "cylinder"
  if (n.includes("ball") || n.includes("apple") || n.includes("orange") || n.includes("sphere")) return "sphere"
  return "box"
}

function WorkspaceObject({ obj, index }) {
  const meshRef = useRef()
  const pos = POSITION_3D[obj.position] || POSITION_3D["center"]
  const scale = SIZE_SCALE[obj.estimated_size] || SIZE_SCALE["medium"]
  const color = COLOR_MAP[obj.color?.toLowerCase()] || "#a1a1aa"
  const shape = useMemo(() => getShape(obj.name), [obj.name])

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.position.y = scale + Math.sin(state.clock.elapsedTime * 1.5 + index * 2) * 0.015
    }
  })

  return (
    <group position={[pos[0], pos[1], pos[2]]}>
      <group ref={meshRef}>
        {shape === "cylinder" && (
          <mesh castShadow>
            <cylinderGeometry args={[scale * 0.6, scale * 0.6, scale * 2, 16]} />
            <meshStandardMaterial color={color} metalness={0.3} roughness={0.6} />
          </mesh>
        )}
        {shape === "sphere" && (
          <mesh castShadow>
            <sphereGeometry args={[scale, 16, 16]} />
            <meshStandardMaterial color={color} metalness={0.2} roughness={0.7} />
          </mesh>
        )}
        {shape === "box" && (
          <mesh castShadow>
            <boxGeometry args={[scale * 0.4, scale * 1.8, scale * 0.4]} />
            <meshStandardMaterial color={color} metalness={0.3} roughness={0.5} />
          </mesh>
        )}
      </group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <ringGeometry args={[scale * 0.3, scale * 1.2, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.2} />
      </mesh>
    </group>
  )
}

function WorkspaceObjects() {
  const scene = useAppStore((s) => s.scene)
  const objects = scene?.objects?.length ? scene.objects : MOCK_OBJECTS

  return (
    <group position={[0, -1.5, 0]}>
      {objects.map((obj, i) => (
        <WorkspaceObject key={obj.id} obj={obj} index={i} />
      ))}
    </group>
  )
}

function WorkspaceTable() {
  return (
    <group position={[0, -1.5, 0]}>
      {/* Table surface */}
      <mesh position={[0, -0.05, 0.3]} receiveShadow>
        <boxGeometry args={[5.5, 0.08, 3.5]} />
        <meshStandardMaterial color="#d4d4d8" metalness={0.05} roughness={0.9} />
      </mesh>
      {/* Grid mesh */}
      <gridHelper args={[5.5, 22, "#52525b", "#3f3f46"]} position={[0, 0.0, 0.3]} />
      {/* Position zone rings */}
      {Object.entries(POSITION_3D).map(([name, pos]) => (
        <group key={name} position={[pos[0], 0.01, pos[2]]}>
          <mesh rotation={[-Math.PI / 2, 0, 0]}>
            <ringGeometry args={[0.2, 0.25, 32]} />
            <meshBasicMaterial color="#60a5fa" transparent opacity={0.2} />
          </mesh>
          <mesh rotation={[-Math.PI / 2, 0, 0]}>
            <circleGeometry args={[0.2, 24]} />
            <meshBasicMaterial color="#60a5fa" transparent opacity={0.04} />
          </mesh>
        </group>
      ))}
      {/* Arm reach arc */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}>
        <ringGeometry args={[2.3, 2.35, 64]} />
        <meshBasicMaterial color="#f59e0b" transparent opacity={0.12} />
      </mesh>
      <ContactShadows position={[0, 0.01, 0]} opacity={0.3} scale={8} blur={2.5} far={4} />
    </group>
  )
}

export function ArmSimulation() {
  return (
    <div className="h-full w-full overflow-hidden">
      <Canvas
        camera={{ position: [3, 2.5, 4], fov: 45 }}
        dpr={[1, 2]}
        gl={{ antialias: true }}
        shadows
      >
        <color attach="background" args={["#0a0a0a"]} />
        <fog attach="fog" args={["#0a0a0a", 10, 18]} />

        <ambientLight intensity={0.7} />
        <directionalLight position={[5, 10, 5]} intensity={1.8} castShadow />
        <directionalLight position={[-4, 6, -2]} intensity={0.6} />
        <pointLight position={[-3, 4, -3]} intensity={0.4} color="#60a5fa" />
        <pointLight position={[3, 2, 3]} intensity={0.3} color="#a78bfa" />
        <hemisphereLight args={["#93c5fd", "#fde68a", 0.35]} />

        <SO101Arm />
        <WorkspaceTable />
        <WorkspaceObjects />

        <OrbitControls
          enablePan={false}
          minDistance={3}
          maxDistance={10}
          minPolarAngle={0.3}
          maxPolarAngle={1.4}
          autoRotate
          autoRotateSpeed={0.5}
        />
      </Canvas>
    </div>
  )
}
