# Agenthon Coding 與 Forecasting：從零到可競爭提交的技術行動計畫

## 執行摘要

你們現在最重要的不是「先把 Docker 學懂」，而是先把 **官方評測契約 → 本地可重現評測 → 最小 Agent → Docker 封裝 → 提交** 這條完整鏈打通，再把絕大多數工程投入真正決定分數的核心：T1 的 `讀題 → 規劃 → 寫 code → 執行 → 驗證 → 修復`，以及 T2 的 `數字 baseline → 文字 regime 推論 → 分布調整 → joint sampling`。截至 **2026 年 9 月 21 日**，公開榜 T1 第一名 in3lab 為 **0.8621**、第二名為 **0.2414**，顯示目前存在非常大的方法差距；T2 官網第一名顯示為 **-0.9989**，但官網特別說明 T2 leaderboard 顯示值經轉換為「越高越好」，不能把它直接當 raw CRPS composite 解讀。官方 raw T2 指標仍是 `0.5×CRPS + 0.3×Variogram + 0.2×Tail`，**越低越好**。citeturn11view0turn12view5 本次研究沒有找到可驗證的 in3lab 或 DKYnumber1 公開 solver artifact，因此以下方案不猜測第一名內部實作，而是直接從官方 repo、scorer、submission contract、House Model contract 與公開 practice tasks 反推最合理的工程架構。核心結論是：**T1 不要做一次性大 prompt，而要做 bounded modular repair agent；T2 不要一開始上神經模型，而要先做 regime-aware joint block-bootstrap/scenario mixture，再讓 House LLM 只負責把文字轉成少量可控的 distribution knobs。**

## 目標、成功標準與總體架構

### 官方真正評什麼

T1 是 binary success。每一個 hidden task 只執行一次，必須通過 `g0 → g1 → g2 → g3`，才得到該題 `1.0`；crash、timeout、錯誤 output、pytest 失敗都留在 denominator 內算 `0`，最後 leaderboard 是 mean pass@1。官方沒有 T1 baseline agent。citeturn12view0turn13view1

T2 則提交完整 Monte Carlo predictive distribution，而不是 point forecast。正式 raw score 為：

\[
S =
0.5\,CRPS_{\text{marginal}}
+0.3\,S_{\text{variogram}}
+0.2\,P_{\text{tail}}
\]

多 cell task 的 tail 是 1%、5%、95%、99% quantile 的 **mean pinball loss**；single-cell task 因 Variogram 沒有第二個 cell 可比較，實際權重重分配為約 `0.714 × CRPS + 0.286 × tail`。正式排名還會用 organizer baseline 的 sealed reference scale 做 normalization，因此你自己算出的 local raw composite **適合做相對比較，但不是 leaderboard 值的精確重製**。citeturn12view9 fileciteturn21file0L2-L2 fileciteturn22file0L7-L18

### 建議的量化成功標準

下面「官方標準」是 contract；「團隊內部標準」是我建議你們拿來決定是否值得提交的工程門檻，不是主辦方規定。

| 項目 | 官方要求 | 建議內部成功標準 |
|---|---|---|
| T1 CLI | `solve --task-dir <path> --out <path>` | 100% public tasks 都能啟動，不因 CLI/path crash |
| T1 admissibility | g0–g3 全過才算該題 1 | 結構性 DNF、schema、permission failure **< 2%** |
| T1 correctness | pass@1 | 本地 public practice reward 比例先超過 **0.50**，之後以 **0.75+** 為競爭目標；stretch goal 接近目前榜首區間 `0.85+` |
| T1 exemplar | 正確 deliverables | `t1-EXAMPLE-bs-greeks-pde` 必須 `reward=1` |
| T1 reproducibility | Final 重跑應一致 | fixed seed/task 下 deterministic tools 一致；Agent 不應因無關 randomness 大幅翻轉 |
| T2 CLI | `forecast --panels ... --text ... --asof ... --out ...` | public 104 directories 中所有可 smoke units 結構 100% 可處理 |
| T2 output | samples，至少 200 draws | 預設 **1,000–2,000 draws**；F4 至少 1,000 |
| T2 schema | `draw, asset, horizon, value` + meta + rationale | **100% g0–g3 smoke pass** |
| T2 distribution | raw composite lower better | 自建 rolling-origin backtest 對 simple numeric baseline 的 composite 改善 **≥10%** |
| T2 text usefulness | 無獨立 text 分數 | F2/F4 historical pseudo-eval 中 full-text vs text-blind composite 改善 **≥5%** |
| T2 joint quality | Variogram 30% | 所有 draw 都覆蓋完整 asset×horizon grid；不得 independent per asset |
| T2 stability | organizer 會做 statistical rerun | 固定 LLM signal fixture 後 numeric sampler bit-reproducible；live LLM rerun的分布中位數/quantiles 不出現劇烈跳動 |

T2 官方最低 200 draws、一般建議 500+、F4 建議 1,000+；joint cards 每個 draw 必須包含所有 target assets 和 horizons。citeturn12view8 我把內部預設提高到 1,000–2,000，是因為 quantile/tail sampling noise 會隨 draw 數下降，而官方 solver playbook 也建議較高 draw 數以穩定 CRPS；這是在目前「無特定 compute 限制」規劃假設下很便宜的提升。fileciteturn9file0L2-L2

### 整體資料流

官方 T1 container 接收 read-only task、T2 接收 panel/text/as-of，兩者都只能透過 organizer proxy 存取 House endpoint；不存在一般 Internet。citeturn12view2turn13view2

```mermaid
flowchart TD
    A[官方 hidden unit] --> B{Track}

    B -->|T1 Coding| C[Contract / Task Parser]
    C --> D[Problem Classifier]
    D --> E[Planner]
    E --> F[House LLM Coder]
    F --> G[Static Checks]
    G --> H[Execution Sandbox]
    H --> I[Schema + Finance Validators]
    I -->|失敗| J[Failure Packet / Repair]
    J --> F
    I -->|通過| K[/app/output deliverables]

    B -->|T2 Forecasting| L[Card + Panel + Text Parser]
    L --> M[Numeric Baseline]
    L --> N[House LLM Regime Extractor]
    M --> O[Distribution Parameters]
    N --> P[Mean / Vol / Tail / Scenario Knobs]
    O --> Q[Joint Scenario Sampler]
    P --> Q
    Q --> R[forecast.parquet]
    Q --> S[forecast_meta.json]
    Q --> T[forecast_rationale.md]

    K --> U[官方 g0-g3 + T1 pytest/invariants]
    R --> V[官方 g0-g3 + CRPS/Variogram/Tail]
    S --> V
    T --> V
```

你們應該把 Docker 看成這張圖最外面的執行殼，不是演算法本身。正式提交的 image 必須是 `linux/amd64`、帶 `LABEL qfbench2.interface_version="2.0"`、實作正確 verb，並以 immutable SHA-256 digest 指定。citeturn16view0

## 必做技術準備、環境與工程底座

### Repo 與目錄設計

官方 T1/T2 都有獨立 public starter repo。T1 public repo 是 practice tasks，不含 hidden evaluation answers；T2 有 **103 個 practice units 加一個 worked exemplar**，practice 分為 F1/F2/F3/F4 四類。citeturn12view1turn12view6

我建議不要直接把你們自己的 agent code 塞進官方 repo 深處，而是：

```text
agenthon/
├── official/
│   ├── track1-coding-public/
│   └── track2-forecasting-public/
│
├── t1-agent/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── src/
│   │   ├── t1_cli.py
│   │   ├── contract.py
│   │   ├── classifier.py
│   │   ├── planner.py
│   │   ├── coder.py
│   │   ├── executor.py
│   │   ├── repair.py
│   │   ├── output_validator.py
│   │   └── invariants/
│   └── tests/
│
├── t2-agent/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── src/
│   │   ├── t2_cli.py
│   │   ├── panels.py
│   │   ├── text_signal.py
│   │   ├── baseline.py
│   │   ├── regimes.py
│   │   ├── sampler.py
│   │   └── output.py
│   └── tests/
│
└── shared/
    ├── house_client.py
    ├── schemas.py
    ├── logging.py
    └── reproducibility.py
```

這讓官方 repo 可以隨 upstream 更新，而你們自己的 agent 不會跟主辦方測試程式混在一起。

### 官方 exemplar 要做到什麼程度

T1 必須先完整跑通 `t1-EXAMPLE-bs-greeks-pde`。官方明確要求先閱讀該 unit 的 `instruction.md` **與** `checks/test_outputs.py`，因為後者就是你們理解 financial invariants 的最佳樣板。citeturn12view1

尤其不要犯一個很容易致命的錯誤：**T1 output contract 是 per-unit，不是固定 `results.parquet`。** 官方目前甚至特別提醒 exemplar 需要 `results.parquet`，另一個 zero-coupon task 卻要 `results.json`；公開 units 中 CSV/JSON 比 Parquet 普遍，所以 agent 必須從每一題 `instruction.md` 抽取 deliverable contract，不能 hard-code。citeturn16view0

T2 則先跑 `t2-EXAMPLE-ust-curve-1m`，確認自己真的能產生：

```text
forecast.parquet
forecast_meta.json
forecast_rationale.md
```

且 `qfbench2-smoke` 能通過 g0–g3。官方 public data 不提供 realized outcome，因此你本機可以驗證 admissibility，但不能從官方 public exemplar 算出真正 leaderboard accuracy。citeturn12view10turn13view3

### House Model endpoint

截至目前，核准的 House model 是 `nvidia/nemotron-3-super-120b-a12b`，snapshot/revision 為 `rl-030326-fp8`，training cutoff 官方標示 `unpublished`。runtime 不應 hard-code model name，而應使用注入的 `MODEL_NAME`；API 是 OpenAI-compatible：

```text
$MODEL_ENDPOINT/v1/chat/completions
Authorization: Bearer $MODEL_TOKEN
```

citeturn18view0

最小 shared client：

```python
# shared/house_client.py
from __future__ import annotations

import os
from openai import OpenAI


def house_chat(
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 3000,
    temperature: float = 0.0,
) -> str:
    required = ["MODEL_ENDPOINT", "MODEL_TOKEN", "MODEL_NAME"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Missing House environment variables: {missing}")

    client = OpenAI(
        base_url=os.environ["MODEL_ENDPOINT"].rstrip("/") + "/v1",
        api_key=os.environ["MODEL_TOKEN"],
    )

    response = client.chat.completions.create(
        model=os.environ["MODEL_NAME"],
        messages=messages,
        max_tokens=min(max_tokens, 4000),
        temperature=temperature,
        # 不送 tools / web search / retrieval
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("House model returned empty content")
    return content
```

官方目前 House allocation 是每 unit 最多 **25 個 admitted requests**、每 request 最多 **4,000 output tokens**，並有 1,000,000 input / 100,000 output token 的 unit allowance；retry 也可能消耗 request slot。citeturn12view4turn16view0 因此 T1 repair loop 不應是無限 `while failure: call LLM()`，T2 也不應對每一篇新聞各 call 一次。

### 本地模擬官方環境

T1 官方建議的本地方式就是先讓 agent container 寫 output，再由官方 sandbox 跑 checks；`test.sh` 自己 exit 0 不代表答案通過，因此要實際讀 `reward.json`。citeturn13view0

```bash
UNIT="$(cd official/track1-coding-public/units/t1-EXAMPLE-bs-greeks-pde && pwd)"
OUT="$(mktemp -d)"

docker run --rm --network=none \
  -v "$UNIT:/input:ro" \
  -v "$OUT:/app/output" \
  -v "$OUT:/output" \
  agenthon-t1:local \
  solve --task-dir /input --out /app/output

docker run --rm --network=none \
  -e OUTPUT_DIR=/app/output \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$UNIT:/input:ro" \
  -v "$OUT:/app/output" \
  -v "$OUT:/output" \
  finance-bench-sandbox:latest \
  bash /input/checks/test.sh

python - <<'PY' "$OUT/reward.json"
import json, sys
r = json.load(open(sys.argv[1]))
print(r)
raise SystemExit(0 if r.get("reward") == 1 else 1)
PY
```

T2：

```bash
docker run --rm \
  --network=none \
  -v "$(pwd)/official/track2-forecasting-public/units/t2-EXAMPLE-ust-curve-1m:/input:ro" \
  -v "$(pwd)/output:/output" \
  agenthon-t2:local \
  forecast \
    --panels /input/panels \
    --text /input/text \
    --asof 2024-06-28 \
    --out /output/forecast.parquet

qfbench2-smoke \
  official/track2-forecasting-public/units/t2-EXAMPLE-ust-curve-1m/ \
  output/ \
  --track forecasting
```

這和官方文件的 smoke execution contract 一致。citeturn12view10turn13view4

### CI 應該卡住哪些錯誤

CI 不需要 House endpoint 才有價值。相反，你應該將 model dependency mock 掉，讓大部分 structural tests 完全 offline。

```text
commit
  ↓
ruff / compileall / type checks
  ↓
unit tests
  ↓
mock House endpoint contract tests
  ↓
Docker build linux/amd64
  ↓
CLI interface test
  ↓
T1 exemplar end-to-end
  ↓
T2 exemplar g0-g3 smoke
  ↓
reproducibility tests
  ↓
artifact/schema checks
```

最低 merge gate：

| CI Gate | 必須成立 |
|---|---|
| Python | `python -m compileall src` 通過 |
| Unit | 所有 parser / validator / sampler tests 通過 |
| House client | 正確使用 `/v1/chat/completions`、Bearer token，不要求 vendor key |
| Docker | `linux/amd64` 可 build |
| Image label | `qfbench2.interface_version=2.0` |
| T1 CLI | `solve --task-dir ... --out ...` 正常 |
| T1 exemplar | `reward.json.reward == 1` |
| T2 CLI | `forecast ...` 正常 |
| T2 schema | exact grid、types、no NaN/Inf |
| T2 smoke | g0–g3 all pass |
| Network | `--network=none` 下 structural path 不 crash |
| Seed | numeric layer固定 seed 結果一致 |

## Coding 技術路線

### Agent 的核心不是「會寫 Python」，而是 Contract-first

T1 最危險的失敗往往不是公式不會，而是：

```text
題目要 results.json
Agent 寫出數學完全正確的 results.parquet
→ 0 分
```

官方已明確警告不同 units 的 filename、shape、input location 會不同。citeturn16view0

因此第一個模組不應是 `coder.py`，而應該是 `contract.py`。

建議將任何 task 先整理成：

```json
{
  "task_id": "...",
  "category": "...",
  "timeout_sec": 1800,
  "inputs": [
    {
      "path": "...",
      "format": "parquet",
      "columns": ["..."]
    }
  ],
  "outputs": [
    {
      "path": "results.json",
      "format": "json",
      "schema": "..."
    }
  ],
  "required_calculations": ["..."],
  "units": {
    "rate": "decimal",
    "theta": "per_calendar_day"
  },
  "constraints": ["..."],
  "acceptance_clues": ["..."],
  "domain": "fixed-income"
}
```

Contract parser 應結合兩種方法：

**Deterministic layer** 先讀 `instruction.md`、`card.toml`、列出 `/input` 可見檔案並實際 inspect CSV/JSON/Parquet schema。

**LLM layer** 再從自然語言抽取 deliverables、units、corner cases、required calculations。

最後一定由 deterministic validator 檢查 LLM JSON，不准「LLM 說 output 是 parquet，所以就是 parquet」。

### Problem classification

官方 T1 定義十類任務，包括 derivatives-pricing、fixed-income、credit、factor-research、backtesting、risk-management、microstructure、FX、NLP-on-finance、cross-domain。每類都有不同 invariants，例如 fixed income 強調 DV01 consistency，risk management 強調 CVaR/VaR，microstructure 強調 bid/ask ordering，FX 有 triangular arbitrage/CIP。fileciteturn25file0L2-L8 fileciteturn26file1L20-L35

分類器不要只輸出一個 label，而是：

```json
{
  "primary": "fixed-income",
  "secondary": ["risk-management"],
  "methods": ["bootstrap_curve", "bond_pricing", "dv01"],
  "validators": [
    "discount_factor_positive",
    "bond_price_yield_monotonic",
    "dv01_fd_consistency"
  ],
  "confidence": 0.94
}
```

cross-domain 題直接讓 validator set 取 constituent domains 的 union。

### Prompt 架構

我不推薦：

```text
這是題目全文，幫我寫一個完整 solution，確保正確。
```

推薦拆成四種明確角色，但不要真的需要四個不同模型：

**Contract prompt**：只問「輸入、輸出、units、constraints、unknowns」。

**Planner prompt**：禁止產 code，只產演算法、公式、edge cases、validators。

**Coder prompt**：拿 contract + plan 寫實際 solution。

**Repair prompt**：只看 failure packet，提出最小 patch。

例如 Planner system prompt 的核心：

```text
You are the planning component of a quantitative-finance coding agent.

Do NOT write final code.

Given:
1. an extracted task contract,
2. inspected input schemas,
3. available Python packages,

return strict JSON containing:
- mathematical method,
- formulas and conventions,
- edge cases,
- expected numerical scale,
- domain invariants,
- implementation steps,
- likely failure modes.

Never invent an output filename or schema.
If information is absent, mark it unknown.
```

Coder prompt：

```text
You are implementing a sealed quantitative-finance task.

Hard requirements:
- obey CONTRACT exactly;
- read only task inputs;
- write only required deliverables to OUTPUT_DIR;
- preserve required identifiers/order;
- never write reward.json;
- handle NaN/inf and numerical edge cases;
- include deterministic internal validation before exit;
- exit non-zero if no valid deliverable can be produced.

Return only the files requested in the response protocol.
```

Repair prompt 最重要的一句是：

> **Prefer the smallest patch that explains the observed failure; do not rewrite working components unless the failure proves the architecture is wrong.**

### Code generation 與 execution sandbox

不要讓 LLM code 一產生就直接成為 final answer。

建議 pipeline：

```text
generated solution.py
        ↓
AST parse / compile
        ↓
imports check
        ↓
paths check
        ↓
temporary workspace dry run
        ↓
capture stderr/stdout
        ↓
output contract check
        ↓
finance invariants
        ↓
copy valid deliverables to final output
```

可重用 execution wrapper：

```python
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run_generated(
    script: Path,
    *,
    cwd: Path,
    timeout_sec: int,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "PYTHONUNBUFFERED": "1",
    }
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        ["python", str(script)],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_sec,
        check=False,
    )
```

注意正式 evaluation 裡 participant container **看不到 sealed checks**，所以你的 agent 不能靠「跑 hidden pytest 再修」；它必須靠 instruction、input inspection、自己內建 validators 去預測 checker 會抓什麼。官方 verifier 在 agent 結束後才執行 checks。citeturn16view0

### Self-repair loop

推薦上限式 loop：

```text
Contract
  ↓
Plan
  ↓
Generate
  ↓
Compile
  ├─ fail → syntax repair
  ↓
Execute
  ├─ exception → runtime repair
  ↓
Output validation
  ├─ fail → contract repair
  ↓
Finance validation
  ├─ fail → numerical/domain repair
  ↓
PASS
```

Failure packet 不要丟整個歷史 transcript，應只包含：

```json
{
  "failure_type": "financial_invariant",
  "message": "put-call parity max abs error = 0.184",
  "contract": {...},
  "plan_summary": "...",
  "current_code": "...",
  "stdout_tail": "...",
  "stderr_tail": "...",
  "observed_output_schema": {...},
  "failed_checks": [...]
}
```

建議最多保留大約 **8–12 個 House calls 的設計預算**，給 25-request limit 留充分餘裕，而不是把 24 個 request 全花掉才發現最後一次又失敗。官方 admitted retry 也會消耗額度。citeturn16view0

### 常見金融 sanity checks

Exemplar checker 本身已展示 put-call parity、Delta bounds、Gamma/Vega signs、price bounds 與 finite-difference consistency。fileciteturn5file0L2-L2

更完整的可重用 invariant library 可設計成：

| Domain | 常見 invariant | 檢查方法 |
|---|---|---|
| Options | \(C-P=S-Ke^{-rT}\) | paired call/put abs error |
| Options | Call \(\Delta\in[0,1]\)，Put \(\Delta\in[-1,0]\) | range check |
| Options | \(\Gamma\ge0,\ Vega\ge0\) | sign check |
| Options | Call lower bound \(\max(0,S-Ke^{-rT})\) | numerical bound |
| Options | \(C\le S\)，\(P\le Ke^{-rT}\) | no-arbitrage bound |
| Options | strike convexity | finite second differences |
| Greeks | reported Delta/Gamma vs bumped prices | finite differences |
| Fixed income | bond price normally falls as yield rises | bump yield ±1bp |
| Fixed income | par coupon≈yield ⇒ price≈par | synthetic sanity case |
| Fixed income | DV01 ≈ finite-difference price move | central difference |
| Curves | discount factors \(>0\) | range check |
| Swaps | par swap NPV≈0 | reprice at reported par rate |
| Credit | hazard rate ≥0 | range check |
| Credit | survival probability ∈[0,1], non-increasing | range + monotonicity |
| CDS | par premium leg≈protection leg | leg reconciliation |
| Risk | volatility ≥0 | sign |
| Risk | covariance PSD | eigenvalues ≥−tol |
| Risk | loss-convention CVaR ≥ VaR | tail ordering |
| Backtest | no timestamp look-ahead | signal timestamp < execution timestamp |
| Backtest | self-financing accounting | cash + holdings reconciliation |
| Backtest | turnover ≥0 | direct check |
| Factors | long/short neutrality if requested | \(\sum w\) / gross exposure |
| Microstructure | bid ≤ ask | order-book invariant |
| Microstructure | quantity never negative | state invariant |
| Microstructure | fill ≤ available quantity | conservation |
| FX | \(X/Y \times Y/Z \approx X/Z\) | triangular consistency |
| FX | forward vs spot/rates obey task’s CIP convention | reconstruct forward |
| NLP | score/probability range | [0,1], sum-to-one where applicable |
| Any | IDs/order/schema preserved | deterministic contract validator |
| Any | finite values only | `np.isfinite` |

官方 category guide 明確把 dollar-neutral/no-look-ahead、self-financing/no-look-ahead、CVaR ≥ VaR、Bid ≤ Ask、triangular no-arbitrage/CIP 等列為代表性 invariants。fileciteturn25file0L2-L8

這些 invariant **必須 conditional**。例如題目採不同 dividends、compounding、sign conventions、negative rates、American options 時，不能盲目套最簡 Black-Scholes invariant；contract parser 必須先決定 assumptions。

### 設計選擇比較

| 設計 | 優點 | 缺點 | 建議 |
|---|---|---|---|
| 單一巨大 prompt | request 少、實作快 | contract、數學、code 混在一起；錯了難定位 | **不推薦主架構** |
| Planner + Coder | reasoning/coding 分離、容易 repair | 多一個 call | **推薦** |
| Planner + Coder + Critic | 可提前抓公式問題 | token/request 增加 | 難題啟用 |
| Universal solver prompt | 不怕 classifier 錯 | domain knowledge 很散 | 保留 fallback |
| Category-specific prompts | 能注入精準 invariants | classifier 錯可能帶偏 | **Hybrid 推薦** |
| 直接執行 LLM code | latency 最低 | syntax/path/import 問題直接浪費 run | 不推薦 |
| AST/compile → execute | 很便宜抓低級錯 | 抓不到數學 bug | **最低要求** |
| 完整 static analyzer 後再跑 | 安全性更高 | false positive、工程成本大 | 不必過度 |
| 每次失敗重寫全部 | 能逃離壞架構 | 容易破壞已正確部分 | 僅架構錯誤用 |
| targeted patch | 較穩、token 少 | patch 累積可能變髒 | **repair 預設** |
| LLM 自己說「結果合理」 | 很彈性 | 不可重現、不可靠 | 不當 verifier |
| deterministic invariant library | 快、穩、可測 | 要累積 domain checks | **強烈推薦** |

**T1 最終推薦：`deterministic contract parser + modular planner/coder + compile/execute + deterministic validator + bounded repair`。**

## Forecasting 技術路線

### 先理解 T2 的真正數據結構

T2 panels 採 long-format，典型 columns 是：

```text
date
asset
value
panel_id
```

fileciteturn24file0L2-L29

`forecast.parquet` 則必須精確是：

| Column | Type |
|---|---|
| `draw` | int32 |
| `asset` | string |
| `horizon` | int32 |
| `value` | float64 |

`asset` 必須 exactly match card target ID，horizon 也要保持 authored key；最低 200 draws。citeturn12view8

Meta：

```json
{
  "unit_id": "t2-F3-ust-curve-2024Q1",
  "asof": "2024-01-02",
  "asset_ids": ["UST_2Y", "UST_5Y", "UST_10Y", "UST_30Y"],
  "horizons": [21, 63],
  "representation": "samples",
  "n_draws": 1000
}
```

`unit_id`、`asof` 必須跟 card 一致；`forecast_rationale.md` 也必須存在且非空，但目前永遠不參與 composite score。citeturn12view8turn12view9

### Baseline 不應該先押神經模型

官方 repo 裡叫 `chronos.py`、`timesfm.py`、`lag_llama.py`、`moirai.py`、`theta_arima.py` 的五個 baseline files **不是那些模型的真正實作**；目前它們都是 Gaussian random-walk placeholder，因此不要把它們的相對結果當模型比較。citeturn13view2

而且現行 artifact policy 允許一般統計 forecasting code、fitted non-neural linear/tree/GBDT、covariance/calibration parameters；但 Chronos、TimesFM 等 pretrained neural checkpoints **需要 organizer separate approval**。citeturn17view3

因此 MVP 應優先統計/bootstrapping 方法。

### Baseline model 比較

ARIMA 官方定義可處理 AR、MA、integration、seasonal extensions 與 exogenous regressors；ETS/Holt-Winters 專注 level/trend/seasonality；state-space 能用 Kalman framework 建 latent-state models；GARCH 專門將 mean、conditional volatility 與 residual distribution 分開建模。citeturn14view0turn15view0turn15view1turn15view2

| Model | 優點 | 缺點 | T2 適用 | 我的建議 |
|---|---|---|---|---|
| Random walk | 極穩、幾乎不 overfit | 無 mean reversion/regime intelligence | rates/FX baseline | 必須保留做 benchmark |
| ARIMA | 可抓 autocorrelation、mean reversion；成熟 | 單變量傾向、regime/tail 差 | yield/level/return centre | 候選 ensemble |
| ETS | level/trend 簡單穩定 | 金融 daily seasonality通常不強；tail弱 | 平滑 macro/level | 次要 |
| State-space | local level/trend、latent state、missing data 彈性好 | tuning 較複雜 | rates、macro、regime | **很適合進階 baseline** |
| GARCH | volatility clustering、conditional variance | 本身不善於決定長期 mean | FX/factor returns、tail width | **當 volatility layer** |
| IID bootstrap | 保留 empirical distribution | 破壞 temporal autocorrelation | quick baseline | 比 Gaussian 好但不夠 |
| Block bootstrap | 保留短期 serial + cross-asset structure、fat tails | 歷史沒有的 shock 不會自己出現 | 幾乎所有 F1–F4 | **MVP 首選** |
| Neural baseline | 潛在非線性、長 context | checkpoint eligibility、複雜、可能 overfit | 大量 comparable series | **不是現在 MVP** |

官方 solver playbook 自己最強調的其實也是：以 empirical innovations 為 backbone、採約 5–10 day stationary block bootstrap，搭配 recent/full-history regime blend、text-conditioned scenario drift，並對多資產直接模擬 joint paths。fileciteturn9file0L2-L2

所以我會優先做：

> **Joint block bootstrap + recent-vol regime scaling + scenario mixture**

而不是先投入大量時間 AutoARIMA tuning。

### Numeric backbone

每一個 asset/horizon 建議先計算：

```text
spot / current level
daily changes or log returns
historical h-day changes
recent EWMA volatility
full-history volatility
autocorrelation
mean-reversion coefficient
cross-asset covariance / correlation
```

對 `level`：

\[
Y_{t+h}
=
Y_t + \Delta_h
\]

對 `log_return`，官方 reference CLI 的定義是對 daily simple returns 做：

\[
r_t^{log}=\log(1+r_t)
\]

future target 是：

\[
\sum_{j=1}^{h}\log(1+r_{t+j})
\]

不是 future price level。citeturn12view8

### LLM 不要直接預測「未來價格」

House LLM 最適合的工作應縮到：

> **把文字轉成少量結構化 regime parameters。**

推薦 schema：

```json
{
  "regime": {
    "label": "tightening",
    "confidence": 0.78
  },
  "signals": [
    {
      "asset": "UST_2Y",
      "direction": 1,
      "strength": 0.45,
      "volatility_signal": 0.20,
      "tail_direction": "up",
      "confidence": 0.81
    }
  ],
  "scenarios": [
    {
      "name": "higher_for_longer",
      "probability": 0.55,
      "drift_sigma": 0.30,
      "vol_multiplier": 1.10
    },
    {
      "name": "growth_slowdown",
      "probability": 0.30,
      "drift_sigma": -0.20,
      "vol_multiplier": 1.20
    },
    {
      "name": "policy_shock",
      "probability": 0.15,
      "drift_sigma": 0.65,
      "vol_multiplier": 1.50
    }
  ],
  "evidence": [
    {
      "doc_id": "...",
      "signal": "..."
    }
  ]
}
```

這裡最重要的是 `drift_sigma` 使用 **baseline horizon volatility 的倍數**，不要叫 LLM 猜「10Y 應該是 4.32」。如此可降低模型 memorization、unit confusion 與過度自信。

官方 solver guidance 本身也將文字資訊壓成三個主要 knobs：**drift/centre、regime/width、scenario/shape**，且建議 inferred tone 不應讓 distribution 反而變窄。fileciteturn9file0L2-L2

### Text signal → distribution adjustment

假設 numeric baseline 為：

\[
\mu_{0,a,h},\quad
\sigma_{0,a,h},\quad
R_0
\]

可先用一個透明、可 backtest 的規則：

#### Mean

\[
\mu'_{a,h}
=
\mu_{0,a,h}
+
c_\mu s_{a,h}\sigma_{0,a,h}
\]

其中 `s` 是 LLM direction × strength × confidence。

MVP 可對 `c_mu * s` 做 bounded clip，例如只允許 tone inference 移動小於一個 baseline horizon standard deviation；exact cap 應由 historical backtest 校準，不應憑直覺永久寫死。

#### Volatility

讓 LLM 輸出 dimensionless `v∈[-1,1]`：

\[
\sigma'
=
\sigma_0 e^{c_\sigma v}
\]

這比直接 `σ *= 1 + v` 更安全，因為永遠維持 positive。

#### Correlation

不要直接相信 LLM 生成一整張 correlation matrix。

先估 empirical：

\[
R_{\text{emp}}
\]

再讓文字改 scenario/common-factor exposure，最後若需要：

\[
R'
=
(1-\lambda)R_{\text{emp}}
+\lambda R_{\text{scenario}}
\]

最後做 PSD projection：

```python
eigval, eigvec = np.linalg.eigh(corr)
eigval = np.maximum(eigval, 1e-8)
corr_psd = eigvec @ np.diag(eigval) @ eigvec.T
d = np.sqrt(np.diag(corr_psd))
corr_psd = corr_psd / np.outer(d, d)
```

#### Tail

不要只把 Gaussian standard deviation 變大。

可以採：

```text
normal/regime component
+
historical stress bootstrap blocks
+
small-probability scenario component
```

例如 scenario mixture：

\[
F(x)=
\sum_{k=1}^{K}p_kF_k(x)
\]

自然就能產生 skew、fat-tail、甚至 multimodality。

### Joint sampler 比較

| Sampler | Marginal | Dependence | Tail | 優點 | 缺點 | 推薦 |
|---|---|---|---|---|---|---|
| Independent Gaussian | Gaussian | 無 | 薄 | 最簡單 | Variogram 會吃虧 | 不推薦 |
| Multivariate Gaussian | Gaussian | covariance | 薄 | 快、穩 | shock/tail 弱 | baseline |
| Multivariate Student-t | fat-tail | covariance | fat | 簡單改善 tail | 不自然 asymmetry | 好的 fallback |
| Gaussian copula + empirical margins | empirical | flexible | empirical | margins/dependence 分開 | 工程較多 | 進階 |
| Joint block bootstrap | empirical | empirical | empirical | 保留共同 shocks | 不會創造 unseen shock | **推薦 MVP** |
| Scenario mixture + Gaussian | mixture | scenario corr | 可 fat | 容易控制 text effect | base shock 太 parametric | 良好 |
| Scenario mixture + block bootstrap | empirical mixture | empirical + scenario | **最好控制** | 對 F2/F3/F4 很自然 | 參數較多 | **主力推薦** |

F3/F4 特別不能對每個 asset 各自 sampling；官方明確要求同 draw index 是完整 joint outcome，因為 Variogram 會看 co-movement。citeturn12view8turn12view9

### 多 horizon 的正確方式

不要：

```text
21d forecast independently sample
63d forecast independently sample
126d forecast independently sample
```

應模擬完整 path：

```text
day 1
day 2
...
day 21 → 取 horizon 21
...
day 63 → 取 horizon 63
...
day 126 → 取 horizon 126
```

這樣自然保留：

```text
cross-asset correlation
+
cross-horizon dependence
```

官方 solver playbook同樣建議 longer horizon 應建立在 shorter horizon path 的 continuation 上，而不是各 marginal 獨立抽樣。fileciteturn9file0L2-L2

### Draw 數量

| 情況 | 建議 |
|---|---:|
| Contract minimum | 200 |
| 最小 practical | 500 |
| 一般 MVP | 1,000 |
| 主力提交 | 2,000 |
| F4/tail-heavy | 2,000–5,000，視 runtime |
| local parameter search | 可降到 500，再對 finalist 重新 2,000+ |

官方明確要求最低 200，建議 500+，F4 1,000+。citeturn12view8

## 測試、驗證與共同風險控制

### 必做測試矩陣

| 類型 | Track | 範例輸入 | 期望行為 |
|---|---|---|---|
| Unit | T1 parser | instruction 要 `results.json` | contract 不可產 `results.parquet` |
| Unit | T1 parser | rate = 5% / decimal 0.05 | units 被明確記錄 |
| Unit | T1 schema | required columns 缺一欄 | validator fail，不送 final |
| Unit | T1 math | BS matched call/put | parity error < tolerance |
| Unit | T1 math | yield +1bp | bond price direction合理 |
| Unit | T1 executor | generated syntax error | compile stage攔下 |
| Unit | T1 executor | infinite loop | subprocess timeout |
| Unit | T1 repair | NameError | failure packet分類 runtime |
| Unit | T1 repair | correct code, wrong filename | contract repair，不重寫 math |
| Integration | T1 | official exemplar | reward = 1 |
| Adversarial | T1 | misleading filename | parser依 instruction/schema，不依副檔名猜 |
| Adversarial | T1 | extreme short maturity | no NaN/Inf |
| Adversarial | T1 | very large/small values | numerical stable |
| Unit | T2 panel | duplicate asset/date | deterministic reject/aggregate rule |
| Unit | T2 cutoff | row > asof | refuse / filter according to trusted contract |
| Unit | T2 target | `log_return` | 不輸出 price level |
| Unit | T2 sampler | 4 assets ×2 horizons×1000 draws | exactly 8000 rows |
| Unit | T2 sampler | corr matrix non-PSD | projection yields PSD |
| Unit | T2 text | malformed LLM JSON | validate → one bounded retry/fallback |
| Unit | T2 text | conflicting hawkish/dovish docs | confidence下降 / width變寬 |
| Unit | T2 tail | shock signal | tail width應大於 baseline |
| Integration | T2 | exemplar | g0–g3 pass |
| Adversarial | T2 | independent samplers | test 應檢出 joint correlation collapse |
| Adversarial | T2 | shuffled input order | forecast statistics invariant |
| Adversarial | T2 | missing target history | related-series/fallback path，不 crash |
| Repro | Both | same QFBENCH_SEED | numeric layer repeatable |

### 本地重建簡化版 T2 scorer

目前官方 Track 2 canonical tail metric 是 pinball；shared CRPS code使用 fair ensemble estimator，而 Variogram default order 是 \(p=0.5\)。fileciteturn19file0L2-L2 fileciteturn21file0L2-L2

你們可以放一個 `tests/local_t2_metrics.py`：

```python
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def crps_marginal(
    samples: NDArray[np.float64],
    y: NDArray[np.float64],
) -> float:
    """
    samples: [n_draws, n_cells]
    y:       [n_cells]
    Fair ensemble CRPS, matching the public shared implementation.
    """
    samples = np.asarray(samples, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    m = samples.shape[0]
    term1 = np.abs(samples - y[None, :]).mean(axis=0)

    xs = np.sort(samples, axis=0)
    i = np.arange(1, m + 1, dtype=np.float64)
    coef = (2.0 * i - m - 1.0)[:, None]

    pair_sum = 2.0 * np.sum(coef * xs, axis=0)
    denom = m * (m - 1) if m > 1 else m * m
    mean_pair_abs = pair_sum / denom

    crps = term1 - 0.5 * mean_pair_abs
    return float(np.mean(crps))


def variogram_score(
    samples: NDArray[np.float64],
    y: NDArray[np.float64],
    *,
    p: float = 0.5,
) -> float:
    samples = np.asarray(samples, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    realized = np.abs(y[:, None] - y[None, :]) ** p
    forecast = (
        np.abs(samples[:, :, None] - samples[:, None, :]) ** p
    ).mean(axis=0)

    return float(np.sum((realized - forecast) ** 2))


def tail_pinball(
    samples: NDArray[np.float64],
    y: NDArray[np.float64],
    levels=(0.01, 0.05, 0.95, 0.99),
) -> float:
    samples = np.asarray(samples, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    losses = []
    for tau in levels:
        q = np.quantile(samples, tau, axis=0)
        loss = np.where(
            y >= q,
            tau * (y - q),
            (1.0 - tau) * (q - y),
        )
        losses.append(float(np.mean(loss)))

    return float(np.mean(losses))


def raw_composite(
    samples: NDArray[np.float64],
    y: NDArray[np.float64],
) -> dict[str, float]:
    m = crps_marginal(samples, y)
    t = tail_pinball(samples, y)

    if y.size == 1:
        # Single-cell: joint term has no meaning.
        j = 0.0
        score = (5.0 / 7.0) * m + (2.0 / 7.0) * t
    else:
        j = variogram_score(samples, y)
        score = 0.5 * m + 0.3 * j + 0.2 * t

    return {
        "marginal_crps": m,
        "joint_variogram": j,
        "tail_pinball": t,
        "raw_composite": score,
    }
```

**重要：這只能做 local relative comparison。** 官方 ranked score 還包含 sealed organizer reference scales；public practice repo沒有那些 realized outcomes與 normalization values。citeturn13view3

### T2 自己建立 pseudo-evaluation

因為 public units 不給答案，你們需要自己做 rolling-origin backtest：

```text
完整歷史 panel
       ↓
選 historical as-of
       ↓
只把 <= as-of 給 forecaster
       ↓
保留未來 h-day 作 realized
       ↓
產 1000~2000 draws
       ↓
算 local CRPS / Variogram / Tail
       ↓
跟 numeric-only baseline 比
```

必須確保 fitting、feature、文字 document 都遵守當時的 as-of；官方 artifact policy 特別要求 historical fitting/calibration 不能使用在該 task cutoff 當時尚未可得的資料或 revised release。citeturn17view3

對 text contribution 再做：

\[
\Delta S
=
S_{\text{text}}
-
S_{\text{text-blind}}
\]

因為 lower is better，所以：

\[
\Delta S < 0
\]

才表示 text 真的改善。

官方也明確表示 text ablation 是實驗，不是 separate leaderboard component。citeturn13view3

### 共同風險與緩解清單

| 風險 | 可能結果 | 具體緩解 | 上線前檢查 |
|---|---|---|---|
| 呼叫 OpenAI/Anthropic/Gemini | proxy拒絕、unit fail | 只用 `MODEL_ENDPOINT` | ☐ grep source 無 vendor URL |
| endpoint 少 `/v1` | HTTP 403 | `rstrip("/") + "/v1"` | ☐ mock test |
| 缺 MODEL_TOKEN | 401 | fail-fast env validation | ☐ startup check |
| House retry 無限 | 25 requests耗盡 | bounded retry + counter | ☐ max call test |
| runtime pip install | 無 Internet | 所有 deps bake image | ☐ `--network=none` run |
| T1 hardcode parquet | 大量 zero | contract-first parser | ☐ JSON/CSV fixtures |
| T1 偷看 checks | Final根本看不到 | 自己維護 invariant library | ☐ agent不讀 `/input/checks` |
| T1 code crash | pass@1=0 | compile + sandbox + repair | ☐ exception fixtures |
| T1 NaN/Inf | g3 fail | `isfinite` validator | ☐ extreme-value suite |
| Numerical cancellation | 邊界值錯 | stable formulas/log1p/expm1 | ☐ stress tests |
| T2 wrong target type | schema/score災難 | explicit level/log_return branch | ☐ both fixture types |
| T2 independent assets | Variogram變差 | joint path sampler | ☐ dependence test |
| T2 thin tails | tail loss變差 | bootstrap/t mixture/scenarios | ☐ 1/5/95/99 quantiles |
| T2 too wide | CRPS變差 | backtest width calibration | ☐ baseline comparison |
| Correlation not PSD | Cholesky crash | shrink + PSD projection | ☐ eigenvalue test |
| LLM invalid JSON | pipeline crash | schema parser + bounded retry | ☐ malformed fixture |
| LLM overconfident | distribution collapse | inference不可縮窄太多 | ☐ width floor |
| T2 neural checkpoint | eligibility risk | statistical baseline；需approval才包 | ☐ artifact inventory |
| Data leakage | DQ/disqualification risk | strict as-of + provenance | ☐ timestamp audit |
| Randomness drift | rerun不穩 | QFBENCH_SEED / RNG plumbing | ☐ repeat test |
| Docker wrong arch | image不能跑 | `--platform linux/amd64` | ☐ inspect manifest |
| Missing interface label | admission fail | Docker LABEL | ☐ docker inspect |
| Volume permission | 無法寫 output | local bind-mount test | ☐ nonempty output |
| Wrong digest/tag | intake拒絕 | submit SHA digest | ☐ anonymous digest pull |
| Extra T2 root files | schema gate風險 | output dir只留三個 required files | ☐ directory whitelist |

目前 agent tracks 沒有一般 Internet，也沒有 vendor API key；BYO model/adapter categories 已被 2026-09-18 ruling 移除，當前 agent submission category 是 `api`。citeturn12view4turn16view0 T2 的例外是符合 artifact policy 的 permitted local numerical/non-neural artifacts；pretrained neural TS checkpoints需另外核准。citeturn17view3

## 最小 Docker、CLI 與提交封裝

### Docker 到底只需要做到什麼

對你們而言 Docker 的成功標準只有：

> **主辦方用同一個 command 啟動 image 時，你的 Python Agent 能讀掛載進來的 input、完成工作、把正確檔案寫到 output。**

官方要求 Linux/amd64 image、`qfbench2.interface_version="2.0"` label、dependencies 內建，而且 submission descriptor 指定 immutable digest；floating tag 不是正式 submission identity。citeturn11view1turn16view0

### 最小 T1 Dockerfile

```dockerfile
FROM python:3.11-slim

LABEL qfbench2.interface_version="2.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src

# 讓官方可以直接執行：
# docker run IMAGE solve --task-dir /input --out /app/output
RUN printf '#!/bin/sh\nexec python -m src.t1_cli "$@"\n' \
      > /usr/local/bin/solve \
    && chmod +x /usr/local/bin/solve

CMD ["solve", "--help"]
```

典型 `requirements.txt`：

```text
numpy
pandas
scipy
pyarrow
openai
pydantic
```

所有 runtime dependency 應在 build 時進 image，因為 evaluation 時沒有一般 Internet。citeturn11view1

### 最小 solve CLI

```python
# src/t1_cli.py
from __future__ import annotations

import argparse
from pathlib import Path

from .agent import solve_task


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()

    task_dir: Path = args.task_dir.resolve()
    out_dir: Path = args.out.resolve()

    if not task_dir.is_dir():
        raise SystemExit(f"Task directory does not exist: {task_dir}")

    instruction = task_dir / "instruction.md"
    if not instruction.is_file():
        raise SystemExit("instruction.md not found")

    out_dir.mkdir(parents=True, exist_ok=True)

    solve_task(
        task_dir=task_dir,
        output_dir=out_dir,
    )


if __name__ == "__main__":
    main()
```

這個 CLI layer **絕對不要** hard-code `results.parquet`；`solve_task` 必須從 instruction contract 決定真正 deliverables。這點是 T1 官方特別警告的 failure mode。citeturn16view0

### 最小 T2 Dockerfile

同樣概念，只改 verb：

```dockerfile
FROM python:3.11-slim

LABEL qfbench2.interface_version="2.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app/src

RUN printf '#!/bin/sh\nexec python -m src.t2_cli "$@"\n' \
      > /usr/local/bin/forecast \
    && chmod +x /usr/local/bin/forecast

CMD ["forecast", "--help"]
```

### 最小 forecast CLI

```python
# src/t2_cli.py
from __future__ import annotations

import argparse
from pathlib import Path

from .forecaster import run_forecast


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--panels", required=True, type=Path)
    p.add_argument("--text", required=True, type=Path)
    p.add_argument("--asof", required=True, type=str)
    p.add_argument("--out", required=True, type=Path)
    return p


def main() -> None:
    args = parser().parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    run_forecast(
        panels_dir=args.panels,
        text_dir=args.text,
        asof=args.asof,
        forecast_path=args.out,
    )


if __name__ == "__main__":
    main()
```

正式 CLI contract 就是：

```text
forecast
  --panels /input/panels
  --text /input/text
  --asof YYYY-MM-DD
  --out /output/forecast.parquet
```

citeturn12view7

### Build 與 Docker Hub

由於官方要求 `linux/amd64`，即使你們有人用 Apple Silicon，也應明確指定 platform。Agenthon submission contract 與 Docker Buildx 都支援這種 build/push workflow。citeturn16view0turn19view0

T1：

```bash
docker buildx build \
  --platform linux/amd64 \
  -t docker.io/YOUR_TEAM/agenthon-t1:dev \
  --push \
  ./t1-agent
```

T2：

```bash
docker buildx build \
  --platform linux/amd64 \
  -t docker.io/YOUR_TEAM/agenthon-t2:dev \
  --push \
  ./t2-agent
```

查 manifest/digest：

```bash
docker buildx imagetools inspect \
  docker.io/YOUR_TEAM/agenthon-t1:dev
```

`imagetools inspect` 是 Docker 官方用來檢視 registry image details/manifest 的命令。citeturn19view1

真正 submission 用：

```text
docker.io/YOUR_TEAM/agenthon-t1@sha256:....
```

概念，不是 floating `:dev` tag。Agenthon intake 明確要求 digest pinning。citeturn11view1

### submission.json

不要從網路上的舊 conformance example 任意複製 category。當前 track docs 與 toolkit ruling 已規定 T1/T2 agent track 使用 `category: "api"`；舊 `byo-small/byo-large` 已不可用。citeturn16view0

建議從**官方當前 starter descriptor**開始改，只把 placeholder 換掉：

```json
{
  "schema_version": "1.0.0",
  "interface_version": "2.0",
  "competition_id": "<use-current-track-starter-value>",
  "team_id": "<derived-team-id>",
  "track": "coding",
  "phase": "dev",
  "category": "api",
  "image": {
    "registry": "docker.io",
    "repository": "YOUR_TEAM/agenthon-t1",
    "digest": "sha256:<64-hex-digest>"
  },
  "image_access": "public",
  "models": [
    {
      "name": "nvidia/nemotron-3-super-120b-a12b",
      "version": "rl-030326-fp8",
      "revision": "rl-030326-fp8",
      "training_cutoff": "unpublished",
      "access": "api"
    }
  ],
  "license": "Apache-2.0",
  "descriptor_digest": "sha256:<generated-by-toolkit>"
}
```

House disclosure 的 exact model metadata 是官方目前發布的值。citeturn18view0

若 T2 完全不呼叫 House 且沒有任何 learned model，artifact policy 允許 `models: []`；若使用 bundled fitted non-neural learned model，就必須如實以 local model disclosure 記錄 provenance/training cutoff。citeturn17view3

不要自己手算 `descriptor_digest`。官方要求改 descriptor 後重新用 toolkit pack。citeturn11view1

完整 packaging：

```bash
qfbench2 submission alias \
  --team-number YOUR_TEAM_NUMBER
```

取得 derived `team_id` 後：

```bash
qfbench2 submission pack \
  --descriptor submission.json \
  --team-number YOUR_TEAM_NUMBER \
  --out submission.zip
```

ZIP 內容不是 Docker image，而是 `submission.json` 與 toolkit 產生的 `team-claim.json`；organizer 另外依 digest pull image。citeturn11view1

### 可直接執行的 pre-submit checklist

| Check | 必須看到 |
|---|---|
| ☐ `docker buildx build --platform linux/amd64` | success |
| ☐ `docker inspect` interface label | `"2.0"` |
| ☐ T1 `solve --help` | exit 0 |
| ☐ T2 `forecast --help` | exit 0 |
| ☐ local run `--network=none` | 不因 runtime download crash |
| ☐ T1 exemplar checker | `reward = 1` |
| ☐ T2 smoke | g0/g1/g2/g3 pass |
| ☐ T2 output dir | 只有 required deliverables |
| ☐ `forecast.parquet` dtype | int32/string/int32/float64 |
| ☐ T2 draw completeness | 每 draw 有完整 asset×horizon |
| ☐ no NaN / ±Inf | 0 個 |
| ☐ House client | 只打 MODEL_ENDPOINT `/v1` |
| ☐ vendor URLs | 0 個 |
| ☐ request counter | 有 hard cap |
| ☐ runtime `pip install` / wget/curl | 0 個 |
| ☐ Docker Hub digest anonymous pull | success |
| ☐ descriptor category | `api` |
| ☐ House model metadata | 與 current official pin 一致 |
| ☐ descriptor digest | toolkit 重新 pack 後產生 |
| ☐ ZIP | submission.json + team proof，沒有 Docker layers/secrets |

## 最小可交付版本與後續優化方向

### T1 最小 MVP

你們第一個真正值得提交的 T1 不需要「懂所有金融」。

它至少要有：

```text
solve CLI
   ↓
instruction/card/files parser
   ↓
structured contract
   ↓
domain classifier
   ↓
House Planner
   ↓
House Coder
   ↓
compile / execute
   ↓
generic output validator
   ↓
basic finance invariants
   ↓
最多數次 targeted repair
   ↓
deliverable
```

**MVP acceptance：**

```text
官方 exemplar reward = 1
+
可處理 JSON / CSV / Parquet output contract
+
不 hardcode input filename
+
syntax/runtime/schema failure 可以 repair
+
至少 derivatives / fixed-income / risk / backtest / FX
有基本 invariant support
+
public tasks 不因 CLI/schema/path 大量 DNF
```

T1 最值得投資的地方不是一開始塞更多 quant formulas，而是把 failure 變成**可分類、可修復、可重現**。

### T2 最小 MVP

我會直接做：

```text
forecast CLI
   ↓
讀 card + forecast spec
   ↓
讀 joint panel
   ↓
baseline empirical h-day distribution
   ↓
recent/full-history volatility blend
   ↓
joint block bootstrap
   ↓
一次 House call：
text → regime/scenarios JSON
   ↓
mean / vol / scenario adjustment
   ↓
1000~2000 joint draws
   ↓
schema validator
   ↓
forecast.parquet
forecast_meta.json
forecast_rationale.md
```

這個 MVP 已經對齊官方 scoring 的三件核心：

```text
CRPS       → baseline center + width
Variogram  → joint bootstrap
Tail       → empirical tails + scenario mixture
```

而且直接符合官方 solver guidance「regime-aware、text-conditioned drift、scenario mixtures、fat tails」的方向。官方 playbook稱其 internal independent-solve evaluation 中，表現最好的 solves 大量使用這些特徵。fileciteturn9file0L2-L2

### 可選高階優化

| Track | 優化 | 預期效益 | 難度 | 優先性 |
|---|---|---:|---:|---|
| T1 | **Adaptive category router**：根據 task 決定 prompt/tool/invariants | 高：減少 universal prompt失誤 | 中 | 高 |
| T1 | **Retrieval-free quant knowledge library**：本地公式/模板/edge-case guide | 高：省 token、穩定公式 | 中 | 高 |
| T1 | **Differential testing**：同一公式用兩種方法交叉驗證 | 高：抓 silent numerical bugs | 中 | 高 |
| T1 | **Repair policy classifier**：syntax/runtime/schema/domain 分開處理 | 高：降低無效重寫 | 中 | 高 |
| T1 | **Metamorphic testing**：輸入 bump、scale、permutation 後檢查合理性 | 高：對 hidden invariants 很有用 | 高 | 高 |
| T2 | **State-space + bootstrap ensemble** | 中高：改善 mean/reversion | 中 | 中高 |
| T2 | **GARCH/EWMA regime vol layer** | 高：改善 CRPS/tail width | 中 | 高 |
| T2 | **Scenario probability calibration**：從 rolling historical cases tune | 高：減少 LLM過度自信 | 高 | 高 |
| T2 | **Empirical copula / Student-t copula** | 中高：改善 joint/tails | 高 | 中 |
| T2 | **Text signal ensemble/ablation controller**：只有 confidence 高時才移 mean | 高：避免文字害 forecast | 中 | 高 |

其中 T2 neural foundation model 暫時不列前十優先項，是因為目前 pretrained Chronos/TimesFM 類 checkpoint 需要 organizer separate approval，而且官方 repo 同名 adapters 目前只是 placeholder。citeturn13view2turn17view3

### 真正應該從哪裡開始

按照「技術依賴關係」而非時間表，你們的順序應該是：

**最高優先：評測契約。**

```text
官方 repo
→ exemplar
→ CLI
→ local mounts
→ g0-g3
→ Docker
→ digest/package
```

這層沒通，Agent 再強也是零。

**第二優先：建立可度量 baseline。**

T1：

```text
每一個 public task
→ reward 0/1
→ failure_type
→ error log
→ category
```

你們應該有自己的 dashboard：

```text
contract failures
schema failures
runtime failures
numerical failures
finance-invariant failures
timeouts
LLM malformed outputs
```

因為 T1 pass@1 是 binary，**「多修掉一類系統性 failure」通常比某一題公式再精準 0.001% 更有價值。**

T2：

```text
numeric-only baseline
vs
text-conditioned forecast
```

在 historical pseudo-units 上固定算：

```text
CRPS
Variogram
Tail
Composite
```

沒有這套 benchmark，你們根本不知道「加 LLM」是在加分還是減分。

**第三優先：Agent intelligence。**

T1 優化：

> contract extraction → planner → coder → verifier → targeted repair。

T2 優化：

> numeric baseline → regime extraction → controlled distribution adjustment → joint sampler。

**第四優先：競爭性 optimization。**

等你們已經能穩定提交、有 score、知道 failure distribution 之後，再做 fancy routing、metamorphic tests、state-space ensemble、GARCH、copula、scenario calibration 等。

這個排序也呼應目前 leaderboard 的訊號：T1 第一名已到 **0.8621**，但第二名只有 **0.2414**。citeturn11view0 這並不能證明第一名用了哪一種 agent architecture；但它至少證明 **這個 benchmark 並不是天然只能解二成左右**。對你們而言最重要的問題因此不是「Docker 要研究多深」，而是儘快讓 Docker 變成一個已解決的 interface 問題，然後把研究能力投入到 **generalizing solver architecture**。

對 T2 則相反：不要被複雜 forecasting model 吸走全部注意力。官方 scoring 清楚地把 **30% 放在 joint structure、20% 放在 tails**，因此一個 point forecast 很準但 asset 各自獨立、tail 太薄的模型，在規則上就不是完整解法。citeturn12view9

整體而言，我會把你們兩個作品的核心定義成：

> **T1：一個會自行驗證與修復的 Quant Coding Agent。**

> **T2：一個以統計模型控制 base distribution、以 House LLM 讀取 regime information、再產生校準 joint scenarios 的 Probabilistic Forecasting Agent。**

而 Docker 只是把這兩台機器各自封裝成主辦方能用固定 `solve` / `forecast` 指令啟動的盒子；正式競爭力來自盒子裡面的 architecture，而不是 Docker 本身。citeturn11view0turn11view1