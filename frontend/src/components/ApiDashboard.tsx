import {
  Activity,
  ArrowRight,
  Box,
  Braces,
  Check,
  Clipboard,
  Database,
  ExternalLink,
  Film,
  LayoutTemplate,
  LoaderCircle,
  Play,
  Search,
  Server,
  Sparkles,
  Tags,
} from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import { feedVideos } from "../data/feedVideos"
import { apiUrl } from "../lib/api"

type HttpMethod = "get" | "post" | "put" | "patch" | "delete"

interface Schema {
  $ref?: string
  type?: string
  title?: string
  description?: string
  default?: unknown
  example?: unknown
  enum?: unknown[]
  properties?: Record<string, Schema>
  required?: string[]
  items?: Schema
  anyOf?: Schema[]
  oneOf?: Schema[]
}

interface Operation {
  tags?: string[]
  summary?: string
  description?: string
  operationId?: string
  parameters?: Array<{
    name: string
    in: string
    required?: boolean
    schema?: Schema
    description?: string
  }>
  requestBody?: {
    required?: boolean
    content?: Record<string, { schema?: Schema }>
  }
  responses?: Record<string, { description?: string; content?: Record<string, { schema?: Schema }> }>
}

interface OpenApiSpec {
  info: { title: string; version: string; description?: string }
  paths: Record<string, Partial<Record<HttpMethod, Operation>>>
  components?: { schemas?: Record<string, Schema> }
}

interface Endpoint {
  path: string
  method: HttpMethod
  operation: Operation
  tag: string
}

interface VideoStatus {
  id: string
  status: string
  frames: number
  objects: number
  candidates: number
}

const METHODS: HttpMethod[] = ["get", "post", "put", "patch", "delete"]

const FLOW_STEPS = [
  {
    icon: LayoutTemplate,
    index: "01",
    title: "匹配预处理户型",
    detail: "模拟上传 room1–7 原图，浏览器计算 SHA-256，与预设清单匹配后取得 sceneId。",
    contract: "GET /api/floorplan/presets",
  },
  {
    icon: Play,
    index: "02",
    title: "刷到家装视频",
    detail: "Feed 用静态列表播放五条 H.264 竖屏视频，并在整个流程中保留 sceneId。",
    contract: "/feed?sceneId=room1",
  },
  {
    icon: Tags,
    index: "03",
    title: "暂停并匹配家具",
    detail: "前端计算 64-bit dHash；返回对象带 prebuiltGlbUrl 时才允许放入户型。",
    contract: "POST /api/feed/detect",
  },
  {
    icon: Box,
    index: "04",
    title: "读取缓存家具",
    detail: "使用 frameId + objectId 解析去重候选和已生成 GLB；缓存不存在直接返回 404。",
    contract: "GET /api/feed/prebuilt-asset",
  },
  {
    icon: Sparkles,
    index: "05",
    title: "同场景组合查看",
    detail: "Space 在同一个 Three.js Scene 加载户型与家具 GLB，并支持位移、旋转、缩放和重置。",
    contract: "/space?sceneId=room1&...",
  },
]

const CORE_CONTRACTS = [
  {
    method: "POST",
    path: "/api/feed/detect",
    title: "暂停识别家具",
    description: "Feed 的核心在线接口。命中 analysis.json 时只做前后帧 dHash 匹配，不调用实时识别模型。",
    request: {
      videoId: "2",
      time: 12.4,
      frameHash: "0f1e2d3c4b5a6978",
    },
    response: {
      frameId: "2_000003",
      frameImageUrl: "/outputs/videos/2/frames/...",
      objects: [
        {
          id: "obj_sofa_001",
          name: "沙发",
          label: "sofa",
          confidence: 0.94,
          bbox: [118, 420, 690, 850],
          tagPosition: [0.43, 0.61],
          deduplicatedCropUrl: "/outputs/videos/2/deduplicated/...",
          prebuiltGlbUrl: "/outputs/videos/2/generated/candidate_sofa_001/generated_model.glb",
        },
      ],
    },
  },
  {
    method: "GET",
    path: "/api/feed/prebuilt-asset",
    title: "读取缓存家具模型",
    description: "比赛主链只查找预生成 GLB，不调用 Ark、Seedream 或 3D Provider；未命中返回 404。",
    request: {
      frameId: "2_000002",
      objectId: "obj_sofa_001",
    },
    response: {
      frameId: "2_000002",
      objectId: "obj_sofa_001",
      deduplicatedObjectId: "candidate_sofa_001",
      glbUrl: "/outputs/videos/2/generated/candidate_sofa_001/generated_model.glb",
      estimatedDimensions: { widthM: 2.2, heightM: 0.85, depthM: 0.9 },
    },
  },
  {
    method: "POST",
    path: "/api/video/preprocess",
    title: "视频离线预处理",
    description: "演示视频入库阶段执行；抽帧/复用人工帧、检测家具、CLIP 去重并写入 analysis.json。",
    request: {
      videoId: "7",
      mode: "ark_grounding",
      reuseExistingFrames: true,
    },
    response: {
      videoId: "7",
      status: "succeeded",
      frameCount: 8,
      detectedObjectCount: 27,
      deduplicatedObjectCount: 12,
      analysisUrl: "/outputs/videos/7/analysis.json",
    },
  },
  {
    method: "GET",
    path: "/api/floorplan/presets",
    title: "读取比赛户型预设",
    description: "返回 room1–7 原图 SHA-256 与静态白模资源。placeholder 模式统一复用 sample_data/floorplans/whitebox.glb。",
    request: {},
    response: {
      presets: [
        {
          sceneId: "room1",
          sourceSha256: "8c0e...",
          whiteboxGlbUrl: "/sample_data/floorplans/preprocessed/room1/whitebox.glb",
          quality: "placeholder",
        },
      ],
    },
  },
]

const SPACE_QUERY = {
  sceneId: "room1",
  videoId: "2",
  time: "12.40",
  sceneType: "living_room",
  frameId: "2_000003",
  objectId: "obj_sofa_001",
  objectLabel: "sofa",
}

function schemaName(schema?: Schema): string {
  if (!schema) return "—"
  if (schema.$ref) return schema.$ref.split("/").at(-1) ?? schema.$ref
  if (schema.anyOf) return schema.anyOf.map(schemaName).join(" | ")
  if (schema.oneOf) return schema.oneOf.map(schemaName).join(" | ")
  if (schema.type === "array") return `${schemaName(schema.items)}[]`
  return schema.title ?? schema.type ?? "object"
}

function methodClass(method: string) {
  return `method method--${method.toLowerCase()}`
}

function operationBody(operation: Operation): Schema | undefined {
  return operation.requestBody?.content?.["application/json"]?.schema
}

function responseSchema(operation: Operation): Schema | undefined {
  const response = operation.responses?.["200"] ?? operation.responses?.["201"]
  return response?.content?.["application/json"]?.schema
}

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      className="copy-button"
      onClick={() => {
        void navigator.clipboard.writeText(value)
        setCopied(true)
        window.setTimeout(() => setCopied(false), 1400)
      }}
      aria-label="复制内容"
    >
      {copied ? <Check aria-hidden="true" /> : <Clipboard aria-hidden="true" />}
      {copied ? "已复制" : "复制"}
    </button>
  )
}

function JsonBlock({ value }: { value: unknown }) {
  const text = JSON.stringify(value, null, 2)
  return (
    <div className="json-block">
      <CopyButton value={text} />
      <pre>{text}</pre>
    </div>
  )
}

export function ApiDashboard() {
  const [spec, setSpec] = useState<OpenApiSpec | null>(null)
  const [health, setHealth] = useState<"checking" | "online" | "offline">("checking")
  const [videoStatuses, setVideoStatuses] = useState<VideoStatus[]>([])
  const [query, setQuery] = useState("")
  const [activeMethod, setActiveMethod] = useState<"all" | HttpMethod>("all")
  const [error, setError] = useState("")

  useEffect(() => {
    let cancelled = false
    Promise.all([
      fetch(apiUrl("/openapi.json")).then((response) => {
        if (!response.ok) throw new Error("OpenAPI 文档读取失败")
        return response.json() as Promise<OpenApiSpec>
      }),
      fetch(apiUrl("/health")).then((response) => {
        if (!response.ok) throw new Error("health check failed")
        return response.json()
      }),
      Promise.all(
        feedVideos.map(async (video): Promise<VideoStatus> => {
          const response = await fetch(apiUrl(`/api/video/analysis/${video.id}`))
          if (!response.ok) {
            return { id: video.id, status: "missing", frames: 0, objects: 0, candidates: 0 }
          }
          const analysis = (await response.json()) as {
            status: string
            frames: Array<{ objects: unknown[] }>
            deduplicatedObjects?: unknown[]
          }
          return {
            id: video.id,
            status: analysis.status,
            frames: analysis.frames.length,
            objects: analysis.frames.reduce((total, frame) => total + frame.objects.length, 0),
            candidates: analysis.deduplicatedObjects?.length ?? 0,
          }
        }),
      ),
    ])
      .then(([openApi, , statuses]) => {
        if (cancelled) return
        setSpec(openApi)
        setHealth("online")
        setVideoStatuses(statuses)
      })
      .catch((caught: unknown) => {
        if (cancelled) return
        setHealth("offline")
        setError(caught instanceof Error ? caught.message : "看板数据读取失败")
      })
    return () => {
      cancelled = true
    }
  }, [])

  const endpoints = useMemo<Endpoint[]>(() => {
    if (!spec) return []
    return Object.entries(spec.paths).flatMap(([path, pathItem]) =>
      METHODS.flatMap((method) => {
        const operation = pathItem[method]
        return operation
          ? [{ path, method, operation, tag: operation.tags?.[0] ?? "other" }]
          : []
      }),
    )
  }, [spec])

  const visibleEndpoints = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    return endpoints.filter((endpoint) => {
      const matchesMethod = activeMethod === "all" || endpoint.method === activeMethod
      const haystack =
        `${endpoint.path} ${endpoint.operation.summary ?? ""} ${endpoint.tag}`.toLowerCase()
      return matchesMethod && (!normalized || haystack.includes(normalized))
    })
  }, [activeMethod, endpoints, query])

  const groupedEndpoints = useMemo(() => {
    const groups = new Map<string, Endpoint[]>()
    visibleEndpoints.forEach((endpoint) => {
      groups.set(endpoint.tag, [...(groups.get(endpoint.tag) ?? []), endpoint])
    })
    return [...groups.entries()]
  }, [visibleEndpoints])

  const totalFrames = videoStatuses.reduce((total, video) => total + video.frames, 0)
  const totalObjects = videoStatuses.reduce((total, video) => total + video.objects, 0)

  return (
    <main className="api-dashboard">
      <header className="dashboard-topbar">
        <a className="dashboard-brand" href="/dashboard">
          <span>R</span>
          <div>
            <strong>ROMBOT</strong>
            <small>FEED HANDOFF BOARD</small>
          </div>
        </a>
        <nav>
          <a href="/feed">
            <Play aria-hidden="true" />
            试用 Feed
          </a>
          <a href="/docs" target="_blank" rel="noreferrer">
            Swagger
            <ExternalLink aria-hidden="true" />
          </a>
        </nav>
      </header>

      <div className="dashboard-shell">
        <section className="dashboard-hero">
          <div>
            <span className="dashboard-kicker">产品、前端、算法统一事实源</span>
            <h1>家装视频 Feed<br />前端交接看板</h1>
            <p>
              从暂停事件到家具 Tag，再到空间页和 3D 生成。这里集中展示当前可用数据、
              页面状态、完整 API 和参数协议。
            </p>
            <div className="hero-actions">
              <a className="hero-primary" href="/feed">
                <Play aria-hidden="true" />
                打开可交互 Feed
              </a>
              <a className="hero-secondary" href="#all-apis">
                <Braces aria-hidden="true" />
                查看全部接口
              </a>
            </div>
          </div>
          <div className="system-card">
            <div className="system-card__top">
              <span className={`health-dot health-dot--${health}`} />
              {health === "online" ? "本地后端在线" : health === "checking" ? "正在检查" : "后端未连接"}
            </div>
            <dl>
              <div>
                <dt>接口总数</dt>
                <dd>{endpoints.length || "—"}</dd>
              </div>
              <div>
                <dt>Feed 视频</dt>
                <dd>{feedVideos.length}</dd>
              </div>
              <div>
                <dt>分析帧</dt>
                <dd>{totalFrames || "—"}</dd>
              </div>
              <div>
                <dt>家具检测</dt>
                <dd>{totalObjects || "—"}</dd>
              </div>
            </dl>
            <div className="system-stack">
              <span>React</span>
              <ArrowRight />
              <span>FastAPI</span>
              <ArrowRight />
              <span>Ark / Hunyuan</span>
            </div>
          </div>
        </section>

        {error && <div className="dashboard-error">{error}。请确认本地 FastAPI 已启动。</div>}

        <section className="dashboard-section">
          <div className="section-heading">
            <div>
              <span>01 / PRODUCT FLOW</span>
              <h2>用户看到的完整链路</h2>
            </div>
            <p>Feed 负责发现和选物；空间页负责生成、摆放和继续编辑。</p>
          </div>
          <div className="flow-grid">
            {FLOW_STEPS.map((step) => (
              <article key={step.index} className="flow-card">
                <div className="flow-card__icon">
                  <step.icon aria-hidden="true" />
                  <span>{step.index}</span>
                </div>
                <h3>{step.title}</h3>
                <p>{step.detail}</p>
                <code>{step.contract}</code>
              </article>
            ))}
          </div>
        </section>

        <section className="dashboard-section">
          <div className="section-heading">
            <div>
              <span>02 / DEMO DATA</span>
              <h2>五条 Feed 演示视频</h2>
            </div>
            <p>全部使用 H.264 竖屏素材，并拥有离线分析缓存。</p>
          </div>
          <div className="video-status-grid">
            {feedVideos.map((video) => {
              const status = videoStatuses.find((item) => item.id === video.id)
              return (
                <article className="video-status-card" key={video.id}>
                  <img src={video.coverUrl} alt="" />
                  <div className="video-status-card__shade" />
                  <div className="video-status-card__content">
                    <div className="video-id">VIDEO {video.id.padStart(2, "0")}</div>
                    <h3>{video.title}</h3>
                    <p>{video.sceneType.replaceAll("_", " ")}</p>
                    <dl>
                      <div><dt>帧</dt><dd>{status?.frames ?? "…"}</dd></div>
                      <div><dt>检测</dt><dd>{status?.objects ?? "…"}</dd></div>
                      <div><dt>候选</dt><dd>{status?.candidates ?? "…"}</dd></div>
                    </dl>
                    <span className={`video-ready ${status?.status === "succeeded" ? "is-ready" : ""}`}>
                      {status?.status === "succeeded" ? "READY" : status?.status ?? "LOADING"}
                    </span>
                  </div>
                </article>
              )
            })}
          </div>
        </section>

        <section className="dashboard-section">
          <div className="section-heading">
            <div>
              <span>03 / CORE CONTRACTS</span>
              <h2>前端必须理解的四个接口</h2>
            </div>
            <p>其余接口在下方自动生成的完整 OpenAPI 区域中查看。</p>
          </div>
          <div className="core-contracts">
            {CORE_CONTRACTS.map((contract) => (
              <article className="contract-card" key={contract.path}>
                <header>
                  <span className={methodClass(contract.method)}>{contract.method}</span>
                  <code>{contract.path}</code>
                </header>
                <h3>{contract.title}</h3>
                <p>{contract.description}</p>
                <div className="contract-columns">
                  <div>
                    <h4>REQUEST</h4>
                    <JsonBlock value={contract.request} />
                  </div>
                  <div>
                    <h4>RESPONSE · 节选</h4>
                    <JsonBlock value={contract.response} />
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="dashboard-section handoff-section">
          <div className="section-heading">
            <div>
              <span>04 / PAGE HANDOFF</span>
              <h2>Feed → Space 跳转协议</h2>
            </div>
            <p>必须携带 frameId 和 objectId，空间页不能重新默认选择第一个家具。</p>
          </div>
          <div className="handoff-board">
            <div className="handoff-url">
              <div>
                <LayoutTemplate aria-hidden="true" />
                <span>GET</span>
                <code>/space?{new URLSearchParams(SPACE_QUERY).toString()}</code>
              </div>
              <CopyButton value={`/space?${new URLSearchParams(SPACE_QUERY).toString()}`} />
            </div>
            <div className="parameter-grid">
              {Object.entries(SPACE_QUERY).map(([name, value]) => (
                <div key={name}>
                  <code>{name}</code>
                  <span>{value}</span>
                  <small>{["videoId", "time", "sceneType", "frameId", "objectId"].includes(name) ? "必传" : "展示字段"}</small>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="dashboard-section states-section">
          <div className="section-heading">
            <div>
              <span>05 / UI STATES</span>
              <h2>设计需要覆盖的页面状态</h2>
            </div>
            <p>这些状态已经在当前可交互原型中实现，视觉同学可直接替换表现层。</p>
          </div>
          <div className="state-list">
            {[
              ["PLAYING", "默认静音播放；当前页之外的视频全部暂停", Film],
              ["PAUSED", "点击画面暂停，开始计算当前帧 dHash", Play],
              ["MATCHING", "等待 /api/feed/detect，显示轻量扫描反馈", LoaderCircle],
              ["TAGGED", "按 object-fit: cover 裁切偏移定位多个家具 Tag", Tags],
              ["EMPTY", "暂停点没有家具，允许重新识别或继续播放", Search],
              ["ERROR", "接口失败不阻塞刷视频，展示可重试反馈", Activity],
            ].map(([name, detail, Icon]) => (
              <article key={name as string}>
                <Icon aria-hidden="true" />
                <div>
                  <strong>{name as string}</strong>
                  <p>{detail as string}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="dashboard-section" id="all-apis">
          <div className="section-heading">
            <div>
              <span>06 / LIVE OPENAPI</span>
              <h2>全部后端接口</h2>
            </div>
            <p>内容直接读取当前 `/openapi.json`，不会与后端代码脱节。</p>
          </div>

          <div className="api-toolbar">
            <label>
              <Search aria-hidden="true" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="搜索路径、功能或分组"
              />
            </label>
            <div className="method-filters">
              {(["all", ...METHODS] as const).map((method) => (
                <button
                  type="button"
                  key={method}
                  className={activeMethod === method ? "active" : ""}
                  onClick={() => setActiveMethod(method)}
                >
                  {method.toUpperCase()}
                </button>
              ))}
            </div>
            <a href="/openapi.json" target="_blank" rel="noreferrer">
              <Database aria-hidden="true" />
              原始 JSON
            </a>
          </div>

          {!spec && !error && (
            <div className="api-loading">
              <LoaderCircle className="spin" />
              正在读取接口定义
            </div>
          )}

          <div className="api-groups">
            {groupedEndpoints.map(([tag, tagEndpoints]) => (
              <section key={tag} className="api-group">
                <header>
                  <Server aria-hidden="true" />
                  <h3>{tag}</h3>
                  <span>{tagEndpoints.length} endpoints</span>
                </header>
                <div>
                  {tagEndpoints.map(({ method, path, operation }) => {
                    const body = operationBody(operation)
                    const output = responseSchema(operation)
                    return (
                      <details className="endpoint-card" key={`${method}-${path}`}>
                        <summary>
                          <span className={methodClass(method)}>{method.toUpperCase()}</span>
                          <code>{path}</code>
                          <strong>{operation.summary ?? operation.operationId ?? "未命名接口"}</strong>
                          <span className="endpoint-arrow">⌄</span>
                        </summary>
                        <div className="endpoint-detail">
                          {operation.description && <p>{operation.description}</p>}
                          <div className="endpoint-meta-grid">
                            <div>
                              <span>REQUEST BODY</span>
                              <strong>{schemaName(body)}</strong>
                              <small>{operation.requestBody?.required ? "required" : body ? "optional" : "none"}</small>
                            </div>
                            <div>
                              <span>SUCCESS RESPONSE</span>
                              <strong>{schemaName(output)}</strong>
                              <small>{Object.keys(operation.responses ?? {}).join(" · ") || "—"}</small>
                            </div>
                            <div>
                              <span>OPERATION ID</span>
                              <strong>{operation.operationId ?? "—"}</strong>
                              <small>{operation.tags?.join(", ") ?? "—"}</small>
                            </div>
                          </div>
                          {operation.parameters?.length ? (
                            <div className="parameter-table">
                              <h4>PARAMETERS</h4>
                              {operation.parameters.map((parameter) => (
                                <div key={`${parameter.in}-${parameter.name}`}>
                                  <code>{parameter.name}</code>
                                  <span>{parameter.in}</span>
                                  <span>{schemaName(parameter.schema)}</span>
                                  <span>{parameter.required ? "required" : "optional"}</span>
                                  <small>{parameter.description}</small>
                                </div>
                              ))}
                            </div>
                          ) : null}
                          {(body || output) && (
                            <div className="schema-links">
                              {body && <span>输入 Schema：<code>{schemaName(body)}</code></span>}
                              {output && <span>输出 Schema：<code>{schemaName(output)}</code></span>}
                              <a href="/docs" target="_blank" rel="noreferrer">在 Swagger 中试调 <ExternalLink /></a>
                            </div>
                          )}
                        </div>
                      </details>
                    )
                  })}
                </div>
              </section>
            ))}
          </div>
          {spec && visibleEndpoints.length === 0 && (
            <div className="api-empty">没有匹配当前筛选条件的接口。</div>
          )}
        </section>

        <footer className="dashboard-footer">
          <div className="dashboard-brand">
            <span>R</span>
            <div><strong>ROMBOT</strong><small>LOCAL HANDOFF BOARD</small></div>
          </div>
          <p>接口定义以运行中的 FastAPI OpenAPI 为准 · 本页面仅用于本地联调与前端设计交接</p>
        </footer>
      </div>
    </main>
  )
}
