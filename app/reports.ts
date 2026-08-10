export type Report = {
  id: string;
  title: string;
  organization: string;
  organizationKind?: "Company" | "University" | "Research Lab" | "Community";
  date: string;
  year: number;
  summary: string;
  tags: string[];
  fields?: string[];
  featured?: boolean;
  openSource?: boolean;
  verification?: "Automated" | "Seed";
  framework?: { sourceUrl?: string; imageUrl?: string; asset?: string; page?: number; caption?: string };
  details?: ReportDetails;
  links: { label: "Report" | "Project" | "GitHub" | "Model" | "Evidence"; url: string }[];
};

export type ReportDetails = {
  keyPoints: string[];
  capabilities: string[];
  metrics: { label: string; value: string; note?: string }[];
};

const fieldMap: Record<string, string> = {
  "VLA": "Vision-language-action",
  "Humanoid": "Humanoid intelligence",
  "World Models": "World models",
  "Manipulation": "Robot manipulation",
  "Tactile": "Tactile intelligence",
  "Datasets": "Data & benchmarks",
  "Dexterous": "Dexterous manipulation",
  "Whole-Body": "Whole-body control",
  "Cross-Embodiment": "Cross-embodiment",
  "Video": "Video models",
};

export function getReportDetails(report: Report): ReportDetails {
  if (report.details) return report.details;
  const fields = report.fields ?? report.tags.map((tag) => fieldMap[tag] ?? tag);
  const evidence = report.summary.match(/\b\d+(?:\.\d+)?\s?(?:B|M|%|Hz|hours?|tasks?)\b/i)?.[0];
  return {
    keyPoints: [report.summary, `Technical scope: ${fields.slice(0, 3).join(" · ")}.`],
    capabilities: ["Embodied perception and decision making", ...fields.slice(0, 2)],
    metrics: evidence
      ? [{ label: "Reported scale / result", value: evidence, note: "Automatically extracted from the primary-source summary." }]
      : [{ label: "Evaluation evidence", value: "See primary technical report", note: "No numerical claim is shown unless it can be reliably extracted." }],
  };
}

export const reports: Report[] = [
  {
    id: "being-h08",
    title: "Being-H0.8",
    organization: "BeingBeyond",
    organizationKind: "Company",
    date: "2026-07-28",
    year: 2026,
    summary: "A latent tactile world-action model that extends large-scale embodied pretraining from visual prediction to touch-aware interaction.",
    tags: ["Tactile", "World Models", "Manipulation"],
    framework: {
      imageUrl: "https://research.beingbeyond.com/being-h08/images/teaser.webp",
      sourceUrl: "https://research.beingbeyond.com/being-h08",
      caption: "官方项目页 Figure 1 · Being-H0.8 visuo-tactile world-action model overview",
    },
    featured: true,
    links: [{ label: "Project", url: "https://research.beingbeyond.com/being-h08" }],
  },
  {
    id: "lingbot-video",
    title: "LingBot-Video",
    organization: "Robbyant",
    organizationKind: "Company",
    date: "2026-07-09",
    year: 2026,
    summary: "A mixture-of-experts video foundation model and pretraining recipe designed around physical realism and embodied tasks.",
    tags: ["World Models", "Video", "Open Source"],
    openSource: true,
    links: [
      { label: "Report", url: "https://arxiv.org/abs/2607.07675" },
      { label: "Project", url: "https://technology.robbyant.com/lingbot-video" },
      { label: "GitHub", url: "https://github.com/robbyant/lingbot-video" },
    ],
  },
  {
    id: "wall-oss-05",
    title: "WALL-OSS-0.5",
    organization: "自变量机器人 / X² Robotics",
    organizationKind: "Company",
    date: "2026-05-29",
    year: 2026,
    summary: "An open 4B VLA that makes pretrained capability directly measurable on real robots before task-specific fine-tuning.",
    tags: ["VLA", "Open Source", "Cross-Embodiment"],
    featured: true,
    openSource: true,
    links: [
      { label: "Report", url: "https://arxiv.org/abs/2605.30877" },
      { label: "Project", url: "https://x2robot.com/en/research" },
      { label: "GitHub", url: "https://github.com/X-Square-Robot/wall-x" },
    ],
  },
  {
    id: "pi07",
    title: "π0.7",
    organization: "Physical Intelligence",
    organizationKind: "Company",
    date: "2026-04-16",
    year: 2026,
    summary: "A steerable generalist robotic foundation model built to follow richer prompts and compose dexterous behaviors in new ways.",
    tags: ["VLA", "Generalist Policy", "Cross-Embodiment"],
    featured: true,
    links: [
      { label: "Report", url: "https://www.pi.website/download/pi07.pdf" },
      { label: "Project", url: "https://www.pi.website/research/pi07" },
    ],
  },
  {
    id: "helix-02",
    title: "Helix 02",
    organization: "Figure",
    organizationKind: "Company",
    date: "2026-01-27",
    year: 2026,
    summary: "A unified visuomotor system connecting onboard vision, touch and proprioception directly to full-body humanoid control.",
    tags: ["Humanoid", "VLA", "Whole-Body"],
    featured: true,
    links: [{ label: "Project", url: "https://www.figure.ai/news/helix-02" }],
  },
  {
    id: "gr00t-n16",
    title: "GR00T N1.6",
    organization: "NVIDIA",
    organizationKind: "Company",
    date: "2025-12-15",
    year: 2025,
    summary: "An open humanoid foundation model update with a larger action expert and broader multi-embodiment pretraining data.",
    tags: ["Humanoid", "VLA", "Open Source"],
    openSource: true,
    links: [
      { label: "Project", url: "https://research.nvidia.com/labs/gear/gr00t-n1_6/" },
      { label: "GitHub", url: "https://github.com/NVIDIA/Isaac-GR00T" },
    ],
  },
  {
    id: "being-h0",
    title: "Being-H0",
    organization: "BeingBeyond",
    organizationKind: "Company",
    date: "2025-07-21",
    year: 2025,
    summary: "A dexterous VLA pretrained from large-scale human video through explicit hand-motion modeling and physical instruction tuning.",
    tags: ["VLA", "Dexterous", "Human Video"],
    openSource: true,
    links: [
      { label: "Report", url: "https://arxiv.org/abs/2507.15597" },
      { label: "Project", url: "https://beingbeyond.github.io/Being-H0/" },
      { label: "GitHub", url: "https://github.com/BeingBeyond/Being-H" },
    ],
  },
  {
    id: "gr00t-n15",
    title: "GR00T N1.5",
    organization: "NVIDIA",
    organizationKind: "Company",
    date: "2025-06-11",
    year: 2025,
    summary: "An improved open foundation model for generalist humanoid robots with stronger grounding, language following and post-training.",
    tags: ["Humanoid", "VLA", "Open Source"],
    openSource: true,
    links: [
      { label: "Project", url: "https://research.nvidia.com/labs/gear/gr00t-n1_5/" },
      { label: "GitHub", url: "https://github.com/NVIDIA/Isaac-GR00T" },
    ],
  },
  {
    id: "smolvla",
    title: "SmolVLA",
    organization: "Hugging Face",
    organizationKind: "Company",
    date: "2025-06-03",
    year: 2025,
    summary: "A compact 450M open VLA designed for accessible training and deployment on consumer robotics hardware.",
    tags: ["VLA", "Efficient", "Open Source"],
    featured: true,
    openSource: true,
    links: [
      { label: "Report", url: "https://arxiv.org/abs/2506.01844" },
      { label: "Project", url: "https://huggingface.co/blog/smolvla" },
      { label: "GitHub", url: "https://github.com/huggingface/lerobot" },
    ],
  },
  {
    id: "helix",
    title: "Helix",
    organization: "Figure",
    organizationKind: "Company",
    date: "2025-02-20",
    year: 2025,
    summary: "A generalist VLA for high-rate continuous control of a humanoid upper body, including wrists, torso, head and fingers.",
    tags: ["Humanoid", "VLA", "Whole-Body"],
    links: [{ label: "Project", url: "https://www.figure.ai/news/helix" }],
  },
  {
    id: "deepseek-r1",
    title: "DeepSeek-R1",
    organization: "深度求索 / DeepSeek",
    organizationKind: "Company",
    date: "2025-01-20",
    year: 2025,
    summary: "DeepSeek-R1 是 DeepSeek 发布的开放推理大语言模型技术报告，核心是以大规模强化学习直接激发并稳定化长链推理，再通过冷启动、拒绝采样和两阶段强化学习提高可读性、通用能力与安全性。",
    tags: ["LLM"],
    fields: ["LLM"],
    openSource: true,
    verification: "Seed",
    details: {
      keyPoints: [
        "DeepSeek-R1-Zero 以基础模型为起点，通过纯强化学习探索自我验证、反思和更长推理链等行为，不依赖人工标注的思维链冷启动数据。",
        "完整 DeepSeek-R1 在冷启动阶段使用少量长链样本改善可读性，随后以数学、代码、推理等可验证任务为主进行强化学习。",
        "训练流程还包含拒绝采样、监督微调与面向有用性和无害性的第二阶段强化学习，以减轻纯强化学习产生的语言混杂和表达问题。",
        "项目同时发布从 R1 蒸馏得到的多种小模型，允许社区在较小模型规模上复用其推理轨迹。",
      ],
      capabilities: [
        "在数学、代码和逻辑推理问题上生成显式的长程推理过程。",
        "通过自我验证和反思调整中间推理步骤。",
        "提供开放权重与蒸馏模型，支持本地部署、研究和商业化使用。",
      ],
      metrics: [
        { label: "主模型规模", value: "671B 总参数，37B 激活参数", note: "DeepSeek-R1 技术报告披露的 MoE 主模型规模。" },
        { label: "AIME 2024", value: "79.8 Pass@1", note: "技术报告列出的数学推理评测结果。" },
        { label: "开放许可", value: "MIT License", note: "官方发布页说明代码和模型以 MIT 许可开放。" },
      ],
    },
    links: [
      { label: "Project", url: "https://api-docs.deepseek.com/news/news250120/" },
      { label: "Report", url: "https://github.com/deepseek-ai/DeepSeek-R1/blob/main/DeepSeek_R1.pdf" },
      { label: "GitHub", url: "https://github.com/deepseek-ai/DeepSeek-R1" },
    ],
  },
  {
    id: "qwen3",
    title: "Qwen3",
    organization: "通义千问 / Qwen",
    organizationKind: "Company",
    date: "2025-04-29",
    year: 2025,
    summary: "Qwen3 是 Qwen 发布的开放大语言模型系列，采用可切换的思考与非思考模式，并覆盖稠密模型和混合专家模型，以在复杂推理、代理调用与低延迟对话之间提供可配置的权衡。",
    tags: ["LLM"],
    fields: ["LLM"],
    openSource: true,
    verification: "Seed",
    details: {
      keyPoints: [
        "Qwen3 通过思考预算控制让同一模型在推理模式与快速回答模式之间切换，而不是为两类交互分别部署模型。",
        "系列同时提供稠密和 MoE 架构，并使用长思维链强化学习、代码与数学任务训练来提升复杂推理。",
        "训练后模型强调多语言、工具调用与代理场景，使语言模型可作为上层规划和调用接口。",
        "官方公开多个尺寸的基础与指令模型，支持社区微调和本地部署。",
      ],
      capabilities: [
        "在思考模式下执行数学、代码和复杂推理。",
        "在非思考模式下以较低延迟完成日常问答与指令跟随。",
        "支持多语言交互、工具调用和代理式任务执行。",
      ],
      metrics: [
        { label: "旗舰 MoE", value: "235B 总参数 / 22B 激活参数", note: "Qwen3-235B-A22B 的官方模型命名与规模。" },
        { label: "小型 MoE", value: "30B 总参数 / 3B 激活参数", note: "Qwen3-30B-A3B 的官方模型命名与规模。" },
        { label: "最小稠密模型", value: "4B", note: "官方发布页列出的 Qwen3 小型模型规模。" },
      ],
    },
    links: [
      { label: "Project", url: "https://qwenlm.github.io/blog/qwen3/" },
      { label: "GitHub", url: "https://github.com/QwenLM/Qwen3" },
    ],
  },
  {
    id: "llama-4",
    title: "Llama 4",
    organization: "Meta",
    organizationKind: "Company",
    date: "2025-04-05",
    year: 2025,
    summary: "Llama 4 是 Meta 发布的原生多模态混合专家大语言模型系列，涵盖 Scout 与 Maverick，并将图像和文本统一输入到长上下文的专家模型中，服务推理、视觉理解与代理应用。",
    tags: ["LLM"],
    fields: ["LLM"],
    openSource: true,
    verification: "Seed",
    details: {
      keyPoints: [
        "Llama 4 Scout 与 Maverick 使用混合专家架构，在较大总参数容量下保持较低的每 token 激活计算量。",
        "模型以原生多模态训练方式联合处理文本与图像，而非在纯文本模型后附加独立视觉模块。",
        "Scout 面向超长上下文，Maverick 面向通用助手、视觉理解与多语言任务。",
        "官方发布开源模型与权重，支持研究、开发与下游适配。",
      ],
      capabilities: [
        "联合理解文本和多张图像。",
        "处理长文档和长上下文任务。",
        "作为通用推理、视觉理解和代理应用的基础模型。",
      ],
      metrics: [
        { label: "Scout", value: "109B 总参数 / 17B 激活参数", note: "官方发布的 Scout MoE 规模。" },
        { label: "Maverick", value: "400B 总参数 / 17B 激活参数", note: "官方发布的 Maverick MoE 规模。" },
        { label: "Scout 上下文", value: "10M tokens", note: "官方发布页披露的最大上下文长度。" },
      ],
    },
    links: [
      { label: "Project", url: "https://ai.meta.com/blog/llama-4-multimodal-intelligence/" },
      { label: "Model", url: "https://www.llama.com/models/llama-4/" },
    ],
  },
  {
    id: "gemma-3",
    title: "Gemma 3",
    organization: "Google DeepMind",
    organizationKind: "Research Lab",
    date: "2025-03-12",
    year: 2025,
    summary: "Gemma 3 是 Google DeepMind 发布的开放轻量级多模态大语言模型系列，基于 Gemini 2.0 的技术，重点在单加速器可部署性、128K 长上下文、视觉理解和多语言能力。",
    tags: ["LLM"],
    fields: ["LLM"],
    openSource: true,
    verification: "Seed",
    details: {
      keyPoints: [
        "Gemma 3 将语言与图像理解能力提供为可在单个 GPU 或 TPU 上运行的开放模型系列。",
        "模型提供 128K 上下文和函数调用能力，适合长文档理解与工具式应用。",
        "系列覆盖从 1B 到 27B 的多个尺度，并提供量化版本以降低部署资源需求。",
        "官方强调其支持 140 多种语言，并提供面向安全的 ShieldGemma 2 配套模型。",
      ],
      capabilities: [
        "在单加速器设备上进行文本和视觉理解。",
        "处理长上下文输入并调用外部函数。",
        "支持多语言交互及本地量化部署。",
      ],
      metrics: [
        { label: "模型尺寸", value: "1B / 4B / 12B / 27B", note: "官方发布的 Gemma 3 系列规模。" },
        { label: "上下文长度", value: "128K tokens", note: "官方发布页披露的最大上下文。" },
        { label: "语言覆盖", value: "140+ 种语言", note: "官方发布页说明的语言支持范围。" },
      ],
    },
    links: [
      { label: "Project", url: "https://blog.google/innovation-and-ai/technology/developers-tools/gemma-3/" },
      { label: "Model", url: "https://ai.google.dev/gemma" },
    ],
  },
  {
    id: "generalist-gen-1",
    title: "GEN-1: Scaling Embodied Foundation Models to Mastery",
    organization: "Generalist AI",
    organizationKind: "Company",
    date: "2026-04-02",
    year: 2026,
    summary: "GEN-1 是 Generalist AI 发布的通用具身基础模型系统。官方称其通过扩大预训练数据与计算、后训练和推理时系统改进，在多项真实操作任务上把平均成功率提升至 99%，并以约 1 小时机器人数据完成各任务适配。",
    tags: ["VLA", "Manipulation", "Datasets"],
    fields: ["Vision-language-action", "Robot manipulation", "Data & benchmarks", "Embodied AI"],
    featured: true,
    verification: "Seed",
    details: {
      keyPoints: [
        "GEN-1 是面向物理世界操作的多模态动作生成系统，而非单一硬件产品；其发布页将模型能力、训练与推理系统共同定义为 GEN-1。",
        "系统在 GEN-0 的基础上继续扩大数据与计算，并整合预训练、后训练、从经验中学习、强化学习、多模态人类指导和推理时技术。",
        "官方称基础预训练使用人类可穿戴设备采集的低成本物理交互数据，GEN-1 针对新任务首次适配相应机器人本体与任务。",
        "其“mastery”评估框架将可靠性、完成速度和面对扰动时的即兴恢复能力作为共同目标。",
        "发布页强调系统级推理与模型编排组件对实际性能的重要性，并非只报告一组静态权重。",
      ],
      capabilities: [
        "在装配、折叠、分拣和包装等真实操作任务中执行端到端视觉动作控制。",
        "用少量任务专属机器人数据适配新任务与新机器人本体。",
        "在物体移位、夹持失败或形变等分布外扰动下恢复任务执行。",
        "以更高动作速度完成灵巧操作，同时维持长时间连续自主运行。",
      ],
      metrics: [
        { label: "平均任务成功率", value: "99%", note: "Generalist 官方发布页称：GEN-1 在所列简单物理任务上达到约 99% 平均成功率，之前模型为 64%。" },
        { label: "任务完成速度", value: "最高约 3×", note: "官方发布页所述相对于此前最佳水平的完成速度提升。" },
        { label: "任务适配数据", value: "约 1 小时机器人数据", note: "官方称所展示结果均以约一小时机器人数据实现任务适配。" },
        { label: "预训练交互数据", value: "50 万+ 小时", note: "官方发布页披露的高保真物理交互数据规模。" },
        { label: "折盒速度", value: "约 12 秒 / 2.8×", note: "官方将 GEN-1 与约 34 秒的此前基线比较。" },
      ],
    },
    links: [
      { label: "Project", url: "https://generalistai.com/blog/gen-1" },
      { label: "Evidence", url: "https://generalistai.com/" },
    ],
  },
];
