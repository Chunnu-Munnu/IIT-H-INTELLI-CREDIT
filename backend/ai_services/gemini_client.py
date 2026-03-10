"""
Gemini AI client — used for:
  1. SWOT synthesis (recommendation orchestrator)
  2. Credit narrative generation (richer than template-based)
  3. SHAP plain-English explanations
  4. Secondary research summarisation
"""
import os
import asyncio
from loguru import logger

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed. Gemini features disabled. pip install google-generativeai")


_client = None

def _get_client():
    global _client
    if _client is None and GEMINI_AVAILABLE:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            logger.warning("GEMINI_API_KEY not set — AI narrative will use template fallback")
            return None
        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        _client = genai.GenerativeModel(model_name)
        logger.info(f"Gemini client initialised | model={model_name}")
    return _client


async def _generate(prompt: str, fallback: str = "") -> str:
    """Run Gemini generation in thread pool (it's sync under the hood)."""
    client = _get_client()
    if client is None:
        return fallback
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: client.generate_content(prompt))
        return response.text.strip()
    except Exception as e:
        logger.warning(f"Gemini generation failed: {e}")
        return fallback


# ── 1. Credit Narrative ──────────────────────────────────────────────────────

async def generate_credit_narrative(
    company_name: str,
    sector: str,
    credit_score: int,
    grade: str,
    default_probability: float,
    five_cs: dict,
    top_shap_features: list,
    ews_flags: list,
    decision: str,
    ratios: list = None,
    financials: list = None,
) -> str:
    """Generate a highly nuanced 5-6 paragraph credit narrative with actionable insights."""

    triggered_flags = [f for f in ews_flags if f.get("triggered")]
    flag_details = "\n".join([f"  - {f.get('flag_name')}: {f.get('reason_evidence')}" for f in triggered_flags[:5]])
    
    ratio_text = ""
    if ratios:
        latest = ratios[0] if isinstance(ratios, list) and len(ratios) > 0 else {}
        ratio_text = "\n".join([f"  - {k}: {v}" for k, v in latest.items() if isinstance(v, (int, float))])

    shap_lines_list = []
    for feat in top_shap_features[:8]:
        if isinstance(feat, dict):
            name = feat.get("feature") or feat.get("feature_name", "Unknown")
            val = feat.get("feature_value", "N/A")
            shap_val = feat.get("shap_value", 0)
            bench = feat.get("benchmark", "N/A")
        else:
            name = str(feat)
            val = "N/A"
            shap_val = 0
            bench = "N/A"
        
        shap_lines_list.append(
            f"  - {name} (Impact: {shap_val:.3f}): Value={val} vs Benchmark {bench}"
        )
    shap_lines = "\n".join(shap_lines_list)

    prompt = f"""You are a Principal Credit Risk Underwriter at a Tier-1 Indian Bank (SBI/HDFC/ICICI level). 
Write a high-fidelity, nuanced Credit Narrative for {company_name} in the {sector} sector.

KEY METRICS:
- Score: {credit_score}/850 | Grade: {grade} | PD: {default_probability*100:.1f}%
- AI System Decision: {decision}

FIVE Cs DIMENSIONS (0-100):
{five_cs}

CRITICAL RISK SIGNALS (EWS):
{flag_details or "No major EWS flags triggered."}

FINANCIAL RATIO SNAPSHOT (Latest FY):
{ratio_text}

EXPLAINABILITY DRIVERS (SHAP):
{shap_lines}

STRUCTURE YOUR RESPONSE INTO THESE SECTIONS (Professional Running Text):
1. EXECUTIVE SUMMARY: A high-level view of the company's credit profile and the core reason for the {decision}.
2. FINANCIAL & CAPACITY ANALYSIS: Nuanced breakdown of repayment capacity (DSCR/ICR/EBITDA) and capital structure (TOL/TNW). Don't just list numbers; explain the trend and industry context.
3. CHARACTER & COMPLIANCE: Discuss the EWS signals, MCA compliance, and legal status. Highlight any "red flags" or "yellow flags" that surfaced.
4. LOAN RECOMMENDATION & MITIGATION: Final rationale. Explicitly state "What the Bank should do" (Special conditions) and "What to monitor" (Pre-emptive steps).

STRICT GUIDELINES:
- Use sophisticated Indian banking terminology (Non-current assets, MPBF, Tandon Committee norms, CMA data, CIRP, NCLT).
- Provide NUANCE. If a ratio is weak, explain if it's a sector-wide trend or a company-specific failure.
- Avoid generic praise. Be critical and balanced. 
- Tone: Formal, analytical, authoritative.
- FORMAT: Clear headings for each of the 4 sections. No bullet points within sections - use cohesive paragraphs."""

    # Build a high-fidelity template-based fallback
    triggered = [f for f in ews_flags if f.get("triggered")]
    risk_summary = "\n".join([f"- {f.get('flag_name', 'Unknown')}: {f.get('reason_evidence', 'N/A')}" for f in triggered[:3]])

    # 🔧 FIX: remove backslash from f-string expression
    ratio_clean = ratio_text.replace("\n", "; ") if ratio_text else ""
    ratio_part = f"(Ratios: {ratio_clean})" if ratio_clean else ""
    
    fallback_sections = [
        f"1. EXECUTIVE SUMMARY: {company_name} is assessed with a {grade} credit grade and a score of {credit_score}/850. The PD is estimated at {default_probability*100:.1f}%. The AI system recommends {decision}.",
        f"2. FINANCIAL & CAPACITY ANALYSIS: Based on the latest FY financials {ratio_part}, the entity exhibits performance consistent with {grade} rating norms. Key strengths include established operations, while leverage ratios require monitoring.",
        f"3. CHARACTER & COMPLIANCE: {f'A total of {len(triggered)} early warning signals were detected, including: ' + ', '.join([f['flag_name'] for f in triggered[:2]]) if triggered else 'No major EWS flags were triggered, indicating stable compliance.'} {flag_details}",
        f"4. LOAN RECOMMENDATION & MITIGATION: Based on the analytical drivers, the proposal is marked as {decision}. Key mitigation includes regular monitoring of current ratios and liquidity triggers."
    ]
    fallback = "\n\n".join(fallback_sections)
    
    result = await _generate(prompt, fallback)
    logger.success(f"[Gemini] Nuanced narrative generated | {len(result)} chars")
    return result


# ── 2. SWOT Generation ───────────────────────────────────────────────────────

async def generate_swot(
    company_name: str,
    sector: str,
    five_cs: dict,
    ews_flags: list,
    ratio_results: list,
    research_items: list,
) -> dict:
    """Generate a structured SWOT with 3–4 bullets per quadrant."""

    triggered = [f for f in ews_flags if f.get("triggered")]
    
    prompt = f"""Generate a professional and highly nuanced SWOT Analysis for a corporate credit proposal.
Company: {company_name}
Sector: {sector}
Five Cs: {five_cs}
EWS Flags Triggered: {[f.get('flag_name') for f in triggered]}
Market Research: {[r.get('title') for r in research_items[:5]]}

CRITICAL REQUIREMENTS:
- Every point must reference a piece of data (e.g., 'Strong DSCR of 1.4x' or 'Negative news regarding X on Source Y').
- Use Indian context.
- Ensure 'Threats' section looks for fraud signals.
- JSON only.
"""

    strengths = [f"Entity operates in the {sector} sector with established market presence."]
    if five_cs.get("Character", 0) > 70: strengths.append("Strong promoter character and compliance track record.")
    if five_cs.get("Capacity", 0) > 70: strengths.append("Robust repayment capacity with healthy cash flow coverage.")

    weaknesses = [f"Detected {len(triggered)} EWS flags requiring intervention."]
    for f in triggered[:2]: weaknesses.append(f"Risk flag triggered: {f.get('flag_name')}.")
    
    opportunities = [f"Potential for market share expansion in the {sector} segment.", "Favorable interest rate environment for top-rated corporate borrowers."]
    
    threats = ["Volatility in raw material pricing or sectoral headwinds.", "Increased competition from established Tier-1 players."]
    if triggered: threats.append("Underlying risk signals could lead to credit deterioration if not mitigated.")

    fallback = {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "opportunities": opportunities,
        "threats": threats,
    }

    text = await _generate(prompt, "")
    if not text:
        return fallback

    import json, re
    try:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group())
    except Exception as e:
        logger.warning(f"Failed to parse SWOT JSON: {e}")

    return fallback


# ── 3. SHAP Plain-English Explanation ───────────────────────────────────────

async def explain_shap_feature(
    feature_name: str,
    feature_value,
    shap_value: float,
    benchmark: str,
    company_name: str,
    sector: str,
) -> str:

    direction = "increases" if shap_value > 0 else "reduces"
    prompt = f"""You are explaining a credit risk factor to a non-technical credit committee member.

Feature: {feature_name}
Entity: {company_name} ({sector})
Actual Value: {feature_value}
Industry Benchmark: {benchmark}
SHAP Impact: {abs(shap_value):.3f} ({direction} default risk)

Write exactly 2 sentences:
1. What this ratio/metric currently shows for this entity vs the benchmark.
2. Why this specifically {direction} the lending risk and what the credit officer should watch.

Be specific with numbers. Use plain English — no jargon without explanation."""

    fallback = (
        f"{feature_name} is {feature_value} against a benchmark of {benchmark}. "
        f"This {'increases' if shap_value > 0 else 'reduces'} default risk by a SHAP magnitude of {abs(shap_value):.3f}."
    )
    return await _generate(prompt, fallback)


# ── 4. Research Summary ──────────────────────────────────────────────────────

async def summarise_research(
    company_name: str,
    sector: str,
    research_items: list,
) -> str:

    if not research_items:
        return f"No secondary research data was scraped for {company_name}."

    items_text = "\n".join(
        f"- [{r.get('sentiment')}] {r.get('title')} (Source: {r.get('source')})"
        for r in research_items[:10]
    )

    prompt = f"""You are a Credit Research Analyst. Synthesise the following secondary research for {company_name} ({sector}).
This summary is for a formal Credit Appraisal Memo.

RESEARCH DATA:
{items_text}

TASK:
Write a professional 3-sentence RAG (Retrieval-Augmented) summary.
1. Primary Sentiment
2. Key Findings
3. Risk Implication

Tone: Objective, concise, data-driven."""

    return await _generate(prompt, f"Secondary research for {company_name} identified {len(research_items)} items across news, regulatory, and sector sources.")


# ── 5. Mitigation & Recommendations ──────────────────────────────────────────

async def generate_recom_mitigation(
    company_name: str,
    sector: str,
    ews_flags: list,
    five_cs: dict,
    decision: str
) -> dict:

    triggered = [f for f in ews_flags if f.get("triggered")]
    
    prompt = f"""Based on the credit analysis of {company_name} ({sector}), provide actionable 'Do's and Don'ts'.

Decision: {decision}
Risk Factors: {[f.get('flag_name') for f in triggered]}
Five Cs: {five_cs}

Return JSON with:
dos, donts, monitoring
"""

    fallback = {
        "dos": ["Obtain promoter guarantee.", "Conduct quarterly stock audit."],
        "donts": ["Avoid unsecured exposure increases.", "Do not release full limit until collateral perfected."],
        "monitoring": ["Monitor DSCR quarterly.", "Track bank statement NACH bounces."]
    }

    text = await _generate(prompt, "")
    if not text: 
        return fallback

    import json, re
    try:
        match = re.search(r'\{[\s\S]*\}', text)
        if match: 
            return json.loads(match.group())
    except:
        pass

    return fallback