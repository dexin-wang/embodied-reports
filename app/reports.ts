export type Report = {
  id: string;
  title: string;
  organization: string;
  date: string;
  year: number;
  summary: string;
  tags: string[];
  featured?: boolean;
  openSource?: boolean;
  links: { label: "Report" | "Project" | "GitHub" | "Model"; url: string }[];
};

export const reports: Report[] = [
  {
    id: "being-h08",
    title: "Being-H0.8",
    organization: "BeingBeyond",
    date: "2026-07-28",
    year: 2026,
    summary: "A latent tactile world-action model that extends large-scale embodied pretraining from visual prediction to touch-aware interaction.",
    tags: ["Tactile", "World Models", "Manipulation"],
    featured: true,
    links: [{ label: "Project", url: "https://research.beingbeyond.com/being-h08" }],
  },
  {
    id: "lingbot-video",
    title: "LingBot-Video",
    organization: "Robbyant",
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
    organization: "X² Robotics",
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
    date: "2025-02-20",
    year: 2025,
    summary: "A generalist VLA for high-rate continuous control of a humanoid upper body, including wrists, torso, head and fingers.",
    tags: ["Humanoid", "VLA", "Whole-Body"],
    links: [{ label: "Project", url: "https://www.figure.ai/news/helix" }],
  },
];
