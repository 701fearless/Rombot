import { useEffect, useRef, useState, useCallback } from "react"
import * as THREE from "three"
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js"
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js"
import {
  ArrowLeft,
  Camera,
  Eye,
  Maximize2,
  Pause,
  Play,
  RotateCcw,
  Sparkles,
  PanelRightClose,
  PanelRightOpen,
} from "lucide-react"

import { FurnitureUploader } from "./FurnitureUploader"
import type { FurnitureUploadItem, UploadedFurnitureWithTransform } from "../types"
import { apiUrl } from "../lib/api"

// ============ 家具定义 ============
interface FurnitureItem {
  id: string
  name: string
  glbUrl: string
  position: [number, number, number]
  rotation: [number, number, number]
  scale?: [number, number, number]
}

// ============ 预设方案 ============
interface DesignScheme {
  id: string
  name: string
  subtitle: string
  style: string
  color: string
  gradient: string
  description: string
  roomType: "living_room" | "bedroom" | "dining" | "study"
  sceneId: string
  furniture: FurnitureItem[]
}

const DESIGN_SCHEMES: DesignScheme[] = [
  // ========== 方案1：现代简约客厅 ==========
  {
    id: "modern-minimal",
    name: "现代简约",
    subtitle: "Modern Minimalist Living",
    style: "less is more",
    color: "#4A90D9",
    gradient: "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
    description: "简洁线条 · 开放空间 · 功能至上",
    roomType: "living_room",
    sceneId: "room1",
    furniture: [
      {
        id: "sofa_main",
        name: "布艺沙发",
        glbUrl: "/outputs/videos/2/generated/candidate_sofa_001/generated_model.glb",
        position: [0, 0, 0.8],
        rotation: [0, Math.PI, 0],
      },
      {
        id: "coffee_table_1",
        name: "茶几",
        glbUrl: "/outputs/videos/2/generated/candidate_coffee_table_001/generated_model.glb",
        position: [0, 0, -0.6],
        rotation: [0, 0, 0],
      },
      {
        id: "rug_1",
        name: "地毯",
        glbUrl: "/outputs/videos/2/generated/candidate_rug_001/generated_model.glb",
        position: [0, -0.02, 0],
        rotation: [0, 0, 0],
        scale: [1.2, 0.02, 1.6],
      },
      {
        id: "cabinet_side",
        name: "边柜",
        glbUrl: "/outputs/videos/2/generated/candidate_cabinet_001/generated_model.glb",
        position: [-2.3, 0, -0.5],
        rotation: [0, Math.PI / 2, 0],
      },
      {
        id: "chair_relax",
        name: "休闲椅",
        glbUrl: "/outputs/videos/2/generated/candidate_chair_001/generated_model.glb",
        position: [1.8, 0, 1.2],
        rotation: [0, -Math.PI / 4, 0],
      },
    ],
  },
  // ========== 方案2：北欧温馨客厅 ==========
  {
    id: "nordic-cozy",
    name: "北欧温馨",
    subtitle: "Nordic Cozy Home",
    style: "hygge life",
    color: "#81B29A",
    gradient: "linear-gradient(135deg, #2d3436 0%, #273c41 50%, #1e3d3f 100%)",
    description: "自然材质 · 温暖色调 · 舒适生活",
    roomType: "living_room",
    sceneId: "room2",
    furniture: [
      {
        id: "sofa_lshape",
        name: "L型沙发",
        glbUrl: "/outputs/videos/2/generated/candidate_sofa_001/generated_model.glb",
        position: [-0.5, 0, 1.0],
        rotation: [0, Math.PI * 0.75, 0],
      },
      {
        id: "coffee_round",
        name: "圆形茶几",
        glbUrl: "/outputs/videos/2/generated/candidate_coffee_table_001/generated_model.glb",
        position: [0.5, 0, -0.3],
        rotation: [0, 0.3, 0],
      },
      {
        id: "rug_nordic",
        name: "编织地毯",
        glbUrl: "/outputs/videos/2/generated/candidate_rug_002/generated_model.glb",
        position: [0, -0.02, 0.2],
        rotation: [0, 0.2, 0],
        scale: [1.4, 0.02, 2.0],
      },
      {
        id: "wardrobe_simple",
        name: "衣柜",
        glbUrl: "/outputs/videos/2/generated/candidate_wardrobe_001/generated_model.glb",
        position: [2.5, 0, -1.8],
        rotation: [0, -Math.PI / 2, 0],
      },
      {
        id: "chair_accent",
        name: "单人椅",
        glbUrl: "/outputs/videos/2/generated/candidate_chair_001/generated_model.glb",
        position: [-1.8, 0, -0.8],
        rotation: [0, Math.PI / 6, 0],
      },
    ],
  },
  // ========== 方案3：新中式雅致 ==========
  {
    id: "chinese-zen",
    name: "新中式",
    subtitle: "Modern Chinese Zen",
    style: "东方美学",
    color: "#C9A96E",
    gradient: "linear-gradient(135deg, #1a1814 0%, #2c2417 50%, #1f1a12 100%)",
    description: "禅意空间 · 对称之美 · 匠心独运",
    roomType: "living_room",
    sceneId: "room3",
    furniture: [
      {
        id: "sofa_zen",
        name: "罗汉榻",
        glbUrl: "/outputs/videos/2/generated/candidate_sofa_001/generated_model.glb",
        position: [0, 0, 1.2],
        rotation: [0, Math.PI, 0],
      },
      {
        id: "table_tea",
        name: "茶几",
        glbUrl: "/outputs/videos/2/generated/candidate_coffee_table_001/generated_model.glb",
        position: [0, 0, -0.4],
        rotation: [0, 0, 0],
      },
      {
        id: "rug_silk",
        name: "丝绒地毯",
        glbUrl: "/outputs/videos/2/generated/candidate_rug_001/generated_model.glb",
        position: [0, -0.02, 0.3],
        rotation: [0, 0, 0],
        scale: [1.0, 0.02, 1.8],
      },
      {
        id: "cabinet_display",
        name: "博古架",
        glbUrl: "/outputs/videos/2/generated/candidate_cabinet_001/generated_model.glb",
        position: [-2.2, 0, -0.8],
        rotation: [0, Math.PI / 2, 0],
      },
      {
        id: "chair_master",
        name: "太师椅",
        glbUrl: "/outputs/videos/2/generated/candidate_chair_001/generated_model.glb",
        position: [2.0, 0, 0.8],
        rotation: [0, -Math.PI / 3, 0],
      },
    ],
  },
  // ========== 方案4：轻奢餐厅 ==========
  {
    id: "luxury-dining",
    name: "轻奢餐厅",
    subtitle: "Luxury Dining Space",
    style: "精致优雅",
    color: "#D4AF37",
    gradient: "linear-gradient(135deg, #1c1c1c 0%, #2a2520 50%, #1f1a15 100%)",
    description: "金属质感 · 大理石纹 · 奢华体验",
    roomType: "dining",
    sceneId: "room4",
    furniture: [
      {
        id: "table_dining",
        name: "餐桌",
        glbUrl: "/outputs/videos/2/generated/candidate_coffee_table_001/generated_model.glb",
        position: [0, 0, 0],
        rotation: [0, 0, 0],
        scale: [1.5, 1, 1.5],
      },
      {
        id: "chair_dine_1",
        name: "餐椅",
        glbUrl: "/outputs/videos/2/generated/candidate_chair_001/generated_model.glb",
        position: [-1.2, 0, 0.8],
        rotation: [0, Math.PI / 4, 0],
      },
      {
        id: "chair_dine_2",
        name: "餐椅",
        glbUrl: "/outputs/videos/2/generated/candidate_chair_001/generated_model.glb",
        position: [1.2, 0, 0.8],
        rotation: [0, -Math.PI / 4, 0],
      },
      {
        id: "cabinet_buffet",
        name: "餐边柜",
        glbUrl: "/outputs/videos/2/generated/candidate_cabinet_001/generated_model.glb",
        position: [-2.4, 0, -1.2],
        rotation: [0, Math.PI / 2, 0],
      },
      {
        id: "rug_dining",
        name: "装饰地毯",
        glbUrl: "/outputs/videos/2/generated/candidate_rug_002/generated_model.glb",
        position: [0, -0.03, 0],
        rotation: [0, 0, 0],
        scale: [2.0, 0.02, 2.0],
      },
    ],
  },
  // ========== 方案5：日式和室 ==========
  {
    id: "japanese-wabi",
    name: "日式和室",
    subtitle: "Japanese Wabi-Sabi",
    style: "侘寂之美",
    color: "#8B7355",
    gradient: "linear-gradient(135deg, #1a1915 0%, #252220 50%, #1a1816 100%)",
    description: "原木元素 · 留白艺术 · 自然共生",
    roomType: "study",
    sceneId: "room5",
    furniture: [
      {
        id: "sofa_low",
        name: "低姿沙发",
        glbUrl: "/outputs/videos/2/generated/candidate_sofa_001/generated_model.glb",
        position: [0, -0.15, 0.6],
        rotation: [0, Math.PI, 0],
        scale: [1.1, 0.7, 1],
      },
      {
        id: "table_low",
        name: "炕桌",
        glbUrl: "/outputs/videos/2/generated/candidate_coffee_table_001/generated_model.glb",
        position: [0, -0.1, -0.5],
        rotation: [0, 0, 0],
        scale: [0.85, 0.7, 0.85],
      },
      {
        id: "rug_tatami",
        name: "榻榻米垫",
        glbUrl: "/outputs/videos/2/generated/candidate_rug_001/generated_model.glb",
        position: [0, -0.05, 0],
        rotation: [0, 0, 0],
        scale: [2.2, 0.05, 2.8],
      },
      {
        id: "cabinet_sliding",
        name: "收纳柜",
        glbUrl: "/outputs/videos/2/generated/candidate_wardrobe_001/generated_model.glb",
        position: [2.6, 0, 0],
        rotation: [0, -Math.PI / 2, 0],
      },
      {
        id: "chair_floor",
        name: "坐垫椅",
        glbUrl: "/outputs/videos/2/generated/candidate_chair_001/generated_model.glb",
        position: [-1.5, -0.1, 0.5],
        rotation: [0, Math.PI / 5, 0],
        scale: [0.8, 0.6, 0.8],
      },
    ],
  },
  // ========== 方案6：工业风 Loft ==========
  {
    id: "industrial-loft",
    name: "工业风Loft",
    subtitle: "Industrial Loft Style",
    style: "粗犷个性",
    color: "#CD853F",
    gradient: "linear-gradient(135deg, #1a1a1a 0%, #2d2a26 50%, #1f1d1a 100%)",
    description: "裸露结构 · 复古金属 · 空间感强",
    roomType: "living_room",
    sceneId: "room6",
    furniture: [
      {
        id: "sofa_leather",
        name: "皮沙发",
        glbUrl: "/outputs/videos/2/generated/candidate_sofa_001/generated_model.glb",
        position: [-0.3, 0, 1.0],
        rotation: [0, Math.PI * 0.9, 0],
      },
      {
        id: "table_metal",
        name: "铁艺茶几",
        glbUrl: "/outputs/videos/2/generated/candidate_coffee_table_001/generated_model.glb",
        position: [0.4, 0, -0.5],
        rotation: [0, 0.15, 0],
      },
      {
        id: "rug_vintage",
        name: "复古地毯",
        glbUrl: "/outputs/videos/2/generated/candidate_rug_002/generated_model.glb",
        position: [0, -0.02, 0.1],
        rotation: [0, 0, 0],
        scale: [1.6, 0.02, 2.2],
      },
      {
        id: "cabinet_locker",
        name: "工业柜",
        glbUrl: "/outputs/videos/2/generated/candidate_cabinet_001/generated_model.glb",
        position: [-2.5, 0, -0.3],
        rotation: [0, Math.PI / 2, 0],
      },
      {
        id: "chair_vintage",
        name: "复古椅",
        glbUrl: "/outputs/videos/2/generated/candidate_chair_001/generated_model.glb",
        position: [2.0, 0, 1.0],
        rotation: [0, -Math.PI / 5, 0],
      },
    ],
  },
]

// 户型白模 URL 映射
function getWhiteboxUrl(sceneId: string): string {
  return `/sample_data/floorplans/preprocessed/${sceneId}/whitebox.glb`
}

export function ShowroomViewer() {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [activeScheme, setActiveScheme] = useState<DesignScheme>(DESIGN_SCHEMES[0])
  const [isLoading, setIsLoading] = useState(true)
  const [loadProgress, setLoadProgress] = useState(0)
  const [isAutoRotate, setIsAutoRotate] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)

  // 自定义（上传）家具相关状态
  const [customFurniture, setCustomFurniture] = useState<UploadedFurnitureWithTransform[]>([])
  const [showSidebar, setShowSidebar] = useState(true)
  const [selectedFurnitureId, setSelectedFurnitureId] = useState<string | null>(null)
  const customModelsRef = useRef<Map<string, THREE.Object3D>>(new Map())

  // 添加自定义家具到场景
  const handleAddCustomFurniture = useCallback((item: FurnitureUploadItem) => {
    const newFurniture: UploadedFurnitureWithTransform = {
      ...item,
      position: [0, 0, 0],
      rotation: [0, 0, 0],
      scale: 1,
    }
    setCustomFurniture((prev) => [...prev, newFurniture])
    
    // 加载模型到场景
    if (sceneRef.current && loaderRef.current) {
      loaderRef.current.load(
        apiUrl(item.glbUrl),
        (gltf) => {
          const model = gltf.scene
          model.name = `custom_${item.id}`
          
          // 初始位置：放在场景中央偏前
          model.position.set(0, 0, 1)
          
          // 启用阴影
          model.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.castShadow = true
              child.receiveShadow = true
            }
          })
          
          sceneRef.current?.add(model)
          customModelsRef.current.set(item.id, model)
          setSelectedFurnitureId(item.id)
        },
        undefined,
        (error) => {
          console.error(`Failed to load custom furniture ${item.name}:`, error)
        }
      )
    }
  }, [])

  // 删除自定义家具
  const handleRemoveCustomFurniture = useCallback((id: string) => {
    setCustomFurniture((prev) => prev.filter((item) => item.id !== id))
    
    // 从场景移除模型
    const model = customModelsRef.current.get(id)
    if (model && sceneRef.current) {
      sceneRef.current.remove(model)
      customModelsRef.current.delete(id)
    }
    if (selectedFurnitureId === id) setSelectedFurnitureId(null)
  }, [selectedFurnitureId])

  // Three.js refs
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const floorModelRef = useRef<THREE.Object3D | null>(null)
  const furnitureModelsRef = useRef<Map<string, THREE.Object3D>>(new Map())
  const animationFrameRef = useRef<number>(0)
  const loaderRef = useRef<GLTFLoader | null>(null)

  // 初始化 Three.js 场景
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let disposed = false

    // 创建场景
    const scene = new THREE.Scene()
    scene.background = new THREE.Color("#0a0b09")
    scene.fog = new THREE.FogExp2("#0a0b09", 0.035)
    sceneRef.current = scene

    // 创建相机
    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.01,
      1000
    )
    camera.position.set(6, 5, 8)
    cameraRef.current = camera

    // 创建渲染器
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.2
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    renderer.setSize(container.clientWidth, container.clientHeight)
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // 控制器
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.06
    controls.minPolarAngle = 0.15
    controls.maxPolarAngle = Math.PI / 2.05
    controls.minDistance = 3
    controls.maxDistance = 20
    controls.autoRotate = true
    controls.autoRotateSpeed = 0.5
    controls.target.set(0, 0.5, 0)
    controlsRef.current = controls

    // 光照系统
    setupLighting(scene)

    // 地面网格
    const gridHelper = new THREE.GridHelper(30, 40, "#2a3028", "#151916")
    gridHelper.position.y = -0.01
    scene.add(gridHelper)

    // Loader
    loaderRef.current = new GLTFLoader()

    // 动画循环
    const animate = () => {
      if (disposed) return
      animationFrameRef.current = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    // Resize handler
    const handleResize = () => {
      if (!container || !camera || !renderer) return
      const width = Math.max(container.clientWidth, 1)
      const height = Math.max(container.clientHeight, 1)
      camera.aspect = width / height
      camera.updateProjectionMatrix()
      renderer.setSize(width, height)
    }
    window.addEventListener("resize", handleResize)

    return () => {
      disposed = true
      cancelAnimationFrame(animationFrameRef.current)
      window.removeEventListener("resize", handleResize)
      controls.dispose()
      renderer.dispose()
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement)
      }
      // 清理模型
      furnitureModelsRef.current.forEach((model) => {
        model.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            child.geometry?.dispose()
            if (Array.isArray(child.material)) {
              child.material.forEach((m) => m.dispose())
            } else {
              child.material?.dispose()
            }
          }
        })
      })
      furnitureModelsRef.current.clear()
    }
  }, [])

  // 设置光照
  function setupLighting(scene: THREE.Scene) {
    // 环境光
    const ambient = new THREE.AmbientLight("#fffef5", 0.4)
    scene.add(ambient)

    // 主光源（模拟窗户光）
    const mainLight = new THREE.DirectionalLight("#ffffff", 1.5)
    mainLight.position.set(8, 12, 6)
    mainLight.castShadow = true
    mainLight.shadow.mapSize.width = 2048
    mainLight.shadow.mapSize.height = 2048
    mainLight.shadow.camera.near = 0.5
    mainLight.shadow.camera.far = 50
    mainLight.shadow.camera.left = -10
    mainLight.shadow.camera.right = 10
    mainLight.shadow.camera.top = 10
    mainLight.shadow.camera.bottom = -10
    scene.add(mainLight)

    // 补光（暖色）
    const fillLight = new THREE.DirectionalLight("#ffeedd", 0.6)
    fillLight.position.set(-6, 4, -4)
    scene.add(fillLight)

    // 顶光
    const topLight = new THREE.PointLight("#f5f0e6", 0.8, 20)
    topLight.position.set(0, 6, 0)
    scene.add(topLight)

    // 边缘光（轮廓）
    const rimLight = new THREE.DirectionalLight("#d7ff67", 0.3)
    rimLight.position.set(-4, 2, 8)
    scene.add(rimLight)
  }

  // 加载户型 + 家具
  useEffect(() => {
    const scheme = activeScheme
    const scene = sceneRef.current
    const loader = loaderRef.current
    if (!scene || !loader || !rendererRef.current) return

    let cancelled = false
    setIsLoading(true)
    setLoadProgress(0)

    // 清除旧家具
    furnitureModelsRef.current.forEach((model) => {
      scene.remove(model)
      model.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.geometry?.dispose()
          if (Array.isArray(child.material)) {
            child.material.forEach((m) => m.dispose())
          } else {
            child.material?.dispose()
          }
        }
      })
    })
    furnitureModelsRef.current.clear()

    // 清除旧户型
    if (floorModelRef.current) {
      scene.remove(floorModelRef.current)
      floorModelRef.current = null
    }

    const whiteboxUrl = getWhiteboxUrl(scheme.sceneId)
    const totalAssets = 1 + scheme.furniture.length
    let loadedCount = 0

    const updateProgress = () => {
      loadedCount++
      setLoadProgress(Math.round((loadedCount / totalAssets) * 100))
    }

    // 加载户型白模
    loader.load(
      whiteboxUrl,
      (gltf) => {
        if (cancelled) return
        const model = gltf.scene

        // 居中模型
        const box = new THREE.Box3().setFromObject(model)
        const center = box.getCenter(new THREE.Vector3())
        model.position.sub(center)

        // 设置材质
        model.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            child.castShadow = true
            child.receiveShadow = true
            if (child.material) {
              const mat = child.material as THREE.MeshStandardMaterial
              mat.color.setHex(0x2a2d28)
              mat.roughness = 0.85
              mat.metalness = 0.05
            }
          }
        })

        scene.add(model)
        floorModelRef.current = model
        updateProgress()

        // 调整相机目标
        const size = box.getSize(new THREE.Vector3())
        const maxDim = Math.max(size.x, size.y, size.z)
        if (cameraRef.current && controlsRef.current) {
          cameraRef.current.position.set(maxDim * 0.5, maxDim * 1.0, maxDim * 0.7)
          controlsRef.current.target.set(0, maxDim * 0.1, 0)
          controlsRef.current.minDistance = maxDim * 0.3
          controlsRef.current.maxDistance = maxDim * 4
        }

        // 加载所有家具
        loadAllFurniture(scheme, scene, loader, updateProgress, () => {
          if (cancelled) return
          setIsLoading(false)
        })
      },
      (progress) => {
        if (progress.total > 0) {
          const pct = Math.round((progress.loaded / progress.total) * 30)
          setLoadProgress(pct)
        }
      },
      (error) => {
        console.error("Failed to load whitebox:", error)
        if (!cancelled) setIsLoading(false)
      }
    )

    return () => {
      cancelled = true
    }
  }, [activeScheme])

  // 批量加载家具
  function loadAllFurniture(
    scheme: DesignScheme,
    scene: THREE.Scene,
    loader: GLTFLoader,
    onItemLoaded: () => void,
    onComplete: () => void
  ) {
    let completed = 0
    const total = scheme.furniture.length

    if (total === 0) {
      onComplete()
      return
    }

    scheme.furniture.forEach((item, index) => {
      loader.load(
        item.glbUrl,
        (gltf) => {
          if (scene.children.length === 0) return // 场景已销毁

          const model = gltf.scene
          model.name = item.id

          // 应用变换
          model.position.set(...item.position)
          model.rotation.set(...item.rotation)
          if (item.scale) {
            model.scale.set(...item.scale)
          }

          // 启用阴影
          model.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.castShadow = true
              child.receiveShadow = true
            }
          })

          scene.add(model)
          furnitureModelsRef.current.set(item.id, model)

          onItemLoaded()
          completed++
          if (completed >= total) {
            onComplete()
          }
        },
        undefined,
        (error) => {
          console.warn(`Failed to load ${item.name}:`, error)
          onItemLoaded()
          completed++
          if (completed >= total) {
            onComplete()
          }
        }
      )
    })
  }

  // 切换自动旋转
  const toggleAutoRotate = () => {
    if (controlsRef.current) {
      controlsRef.current.autoRotate = !isAutoRotate
      setIsAutoRotate(!isAutoRotate)
    }
  }

  // 重置视角
  const resetCamera = () => {
    if (controlsRef.current && cameraRef.current) {
      controlsRef.current.reset()
      cameraRef.current.position.set(6, 5, 8)
      controlsRef.current.target.set(0, 0.5, 0)
      controlsRef.current.update()
    }
  }

  // 全屏切换
  const toggleFullscreen = async () => {
    if (!containerRef.current) return
    try {
      if (!document.fullscreenElement) {
        await containerRef.current.requestFullscreen()
        setIsFullscreen(true)
      } else {
        await document.exitFullscreen()
        setIsFullscreen(false)
      }
    } catch {
      // ignore
    }
  }

  // 截图功能
  const takeScreenshot = () => {
    if (!rendererRef.current) return
    const link = document.createElement("a")
    link.download = `${activeScheme.id}-${Date.now()}.png`
    link.href = rendererRef.current.domElement.toDataURL("image/png")
    link.click()
  }

  return (
    <div className="showroom" data-loading={isLoading} data-sidebar={showSidebar ? "open" : "closed"}>
      {/* 背景渐变 */}
      <div
        className="showroom__bg"
        style={{ background: activeScheme.gradient }}
      />

      {/* 顶部导航 */}
      <header className="showroom__header">
        <a href="/space" className="showroom__back">
          <ArrowLeft size={18} />
          返回
        </a>
        <div className="showroom__brand">
          <Sparkles size={18} style={{ color: activeScheme.color }} />
          <span>ROMBOT SHOWROOM</span>
        </div>
        <div className="showroom__actions">
          <button
            type="button"
            className={`icon-btn ${isAutoRotate ? "is-active" : ""}`}
            onClick={() => setShowSidebar(!showSidebar)}
            title="切换家具面板"
          >
            {showSidebar ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
          </button>
          <button
            type="button"
            className={`icon-btn ${isAutoRotate ? "is-active" : ""}`}
            onClick={toggleAutoRotate}
            title="自动旋转"
          >
            {isAutoRotate ? <Pause size={16} /> : <Play size={16} />}
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={resetCamera}
            title="重置视角"
          >
            <RotateCcw size={16} />
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={takeScreenshot}
            title="截图"
          >
            <Camera size={16} />
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={toggleFullscreen}
            title="全屏"
          >
            <Maximize2 size={16} />
          </button>
        </div>
      </header>

      {/* 主内容区：3D视口 + 侧边栏 */}
      <div className="showroom__main">
        {/* 3D 视口 */}
        <div className="showroom__viewport" ref={containerRef}>
          {isLoading && (
            <div className="showroom__loading">
              <div className="showroom__loading-spinner" />
              <p>正在加载「{activeScheme.name}」方案...</p>
              <div className="showroom__progress">
                <div
                  className="showroom__progress-bar"
                  style={{ width: `${loadProgress}%` }}
                />
              </div>
              <span>{loadProgress}%</span>
            </div>
          )}
        </div>

        {/* 家具上传侧边栏 */}
        {showSidebar && (
          <aside className="showroom__sidebar">
            <FurnitureUploader onAddToScene={handleAddCustomFurniture} />
            
            {/* 场景中的自定义家具列表 */}
            {customFurniture.length > 0 && (
              <div className="scene-furniture-list">
                <h4>场景中的家具 ({customFurniture.length})</h4>
                {customFurniture.map((item) => (
                  <div 
                    key={item.id} 
                    className={`scene-furniture-item ${selectedFurnitureId === item.id ? 'is-selected' : ''}`}
                    onClick={() => setSelectedFurnitureId(item.id)}
                  >
                    <span className="scene-furniture-item__name">{item.name}</span>
                    <button
                      type="button"
                      className="scene-furniture-item__remove"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleRemoveCustomFurniture(item.id)
                      }}
                      title="移除"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </aside>
        )}
      </div>

      {/* 底部方案选择 */}
      <div className="showroom__schemes">
        <div className="showroom__schemes-scroll">
          {DESIGN_SCHEMES.map((scheme) => (
            <button
              key={scheme.id}
              type="button"
              className={`scheme-card ${
                activeScheme.id === scheme.id ? "is-active" : ""
              }`}
              onClick={() => setActiveScheme(scheme)}
              style={{
                "--scheme-color": scheme.color,
              } as React.CSSProperties}
            >
              <div
                className="scheme-card__accent"
                style={{ background: scheme.gradient }}
              />
              <div className="scheme-card__info">
                <h3>{scheme.name}</h3>
                <p>{scheme.subtitle}</p>
              </div>
              <span className="scheme-card__style">{scheme.style}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 当前方案信息 */}
      <div className="showroom__info">
        <div className="showroom__info-main">
          <h2 style={{ color: activeScheme.color }}>{activeScheme.name}</h2>
          <p>{activeScheme.description}</p>
        </div>
        <div className="showroom__info-furniture">
          <Eye size={14} />
          <span>{activeScheme.furniture.length + customFurniture.length} 件家具</span>
          <span>·</span>
          <span>{activeScheme.sceneId.toUpperCase()}</span>
        </div>
      </div>

      {/* 家具清单 */}
      <div className="showroom__furniture-list">
        {activeScheme.furniture.map((item) => (
          <div key={item.id} className="furniture-tag">
            <span className="furniture-tag__dot" style={{ background: activeScheme.color }} />
            {item.name}
          </div>
        ))}
        {customFurniture.map((item) => (
          <div key={`custom-${item.id}`} className="furniture-tag furniture-tag--custom">
            <span className="furniture-tag__dot" style={{ background: "#8B5CF6" }} />
            {item.name}
            <span className="furniture-tag__badge">自</span>
          </div>
        ))}
      </div>
    </div>
  )
}
