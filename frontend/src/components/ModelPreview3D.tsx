import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

export function ModelPreview3D({ glbUrl, name }: { glbUrl: string; name: string }) {
  const hostRef = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')

  useEffect(() => {
    const host = hostRef.current
    if (!host) return
    setStatus('loading')
    let disposed = false
    let animation = 0
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xeeeae3)
    const camera = new THREE.PerspectiveCamera(34, 1, .01, 100)
    camera.position.set(3.4, 2.5, 4.2)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    host.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.autoRotate = true
    controls.autoRotateSpeed = .7
    controls.enablePan = false
    controls.minDistance = 2.4
    controls.maxDistance = 8

    scene.add(new THREE.HemisphereLight(0xffffff, 0x9b9285, 2.8))
    const key = new THREE.DirectionalLight(0xffffff, 4.2)
    key.position.set(4, 7, 5)
    key.castShadow = true
    scene.add(key)
    const fill = new THREE.DirectionalLight(0xd7e2d2, 2)
    fill.position.set(-4, 3, -2)
    scene.add(fill)

    const floor = new THREE.Mesh(
      new THREE.CircleGeometry(3.2, 64),
      new THREE.MeshStandardMaterial({ color: 0xdad5cc, roughness: .9 }),
    )
    floor.rotation.x = -Math.PI / 2
    floor.position.y = -.02
    floor.receiveShadow = true
    scene.add(floor)

    const loader = new GLTFLoader()
    loader.load(glbUrl, ({ scene: model }) => {
      if (disposed) return
      const initial = new THREE.Box3().setFromObject(model)
      const size = initial.getSize(new THREE.Vector3())
      const maxSide = Math.max(size.x, size.y, size.z)
      if (!Number.isFinite(maxSide) || maxSide < 1e-5) {
        setStatus('error')
        return
      }
      model.scale.setScalar(2.5 / maxSide)
      model.updateMatrixWorld(true)
      const fitted = new THREE.Box3().setFromObject(model)
      const center = fitted.getCenter(new THREE.Vector3())
      model.position.set(-center.x, -fitted.min.y, -center.z)
      model.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.castShadow = true
          child.receiveShadow = true
        }
      })
      scene.add(model)
      controls.target.set(0, fitted.getSize(new THREE.Vector3()).y * .42, 0)
      controls.update()
      setStatus('ready')
    }, undefined, () => {
      if (!disposed) setStatus('error')
    })

    const resize = () => {
      const width = Math.max(host.clientWidth, 1)
      const height = Math.max(host.clientHeight, 1)
      renderer.setSize(width, height, false)
      camera.aspect = width / height
      camera.updateProjectionMatrix()
    }
    const observer = new ResizeObserver(resize)
    observer.observe(host)
    resize()

    const render = () => {
      animation = requestAnimationFrame(render)
      controls.update()
      renderer.render(scene, camera)
    }
    render()

    return () => {
      disposed = true
      cancelAnimationFrame(animation)
      observer.disconnect()
      controls.dispose()
      renderer.dispose()
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose()
          const materials = Array.isArray(object.material) ? object.material : [object.material]
          materials.forEach((material) => material.dispose())
        }
      })
      renderer.domElement.remove()
    }
  }, [glbUrl])

  return <div className='model-preview' ref={hostRef} aria-label={`${name} 3D 旋转预览`}>
    {status === 'loading' && <span className='model-preview__status'>正在加载 3D 模型</span>}
    {status === 'error' && <span className='model-preview__status is-error'>模型加载失败</span>}
  </div>
}
