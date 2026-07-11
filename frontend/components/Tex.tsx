"use client";

import { useMemo } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";

/* Our formulas (both the curated explainers and the LLM-generated Paper Card math) are written in a
 * plain unicode notation — superscripts like x², "^(-z)", subscripts wⱼ / y_t, greek η/α/Σ, ‖·‖, etc.
 * toTex() converts that to LaTeX so KaTeX can typeset it properly, instead of showing raw "^" and
 * odd characters. KaTeX renders best-effort (throwOnError:false), so even messy input degrades
 * gracefully rather than crashing. */

const SUP: Record<string, string> = {
  "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8",
  "⁹": "9", "⁻": "-", "⁺": "+", "ⁿ": "n", "ⁱ": "i",
};
const SUB: Record<string, string> = {
  "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7", "₈": "8",
  "₉": "9", "₋": "-", "₊": "+", "ₜ": "t", "ⱼ": "j", "ᵢ": "i", "ₚ": "p", "ₖ": "k", "ₙ": "n",
  "ₐ": "a", "ₑ": "e", "ₒ": "o",
};
const GREEK: Record<string, string> = {
  "α": "\\alpha", "β": "\\beta", "γ": "\\gamma", "δ": "\\delta", "ε": "\\varepsilon", "ζ": "\\zeta",
  "η": "\\eta", "θ": "\\theta", "λ": "\\lambda", "μ": "\\mu", "ν": "\\nu", "π": "\\pi", "ρ": "\\rho",
  "σ": "\\sigma", "τ": "\\tau", "φ": "\\varphi", "χ": "\\chi", "ψ": "\\psi", "ω": "\\omega",
  "Σ": "\\sum", "Π": "\\prod", "Δ": "\\Delta", "Ω": "\\Omega", "Φ": "\\Phi",
};

export function toTex(input: string): string {
  let t = input ?? "";
  t = t.replace(/ŷ/g, "\\hat{y}").replace(/x̂/g, "\\hat{x}").replace(/β̂/g, "\\hat{\\beta}").replace(/ȳ/g, "\\bar{y}");
  t = t.replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺ⁿⁱ]/g, (c) => `^{${SUP[c]}}`);
  t = t.replace(/[₀₁₂₃₄₅₆₇₈₉₋₊ₜⱼᵢₚₖₙₐₑₒ]/g, (c) => `_{${SUB[c]}}`);
  t = t.replace(/\^\(([^)]*)\)/g, "^{$1}").replace(/_\(([^)]*)\)/g, "_{$1}");
  t = t.replace(/\^([A-Za-z0-9.+\-]+)/g, "^{$1}");
  t = t.replace(/(?<![\\{])_([A-Za-z0-9]+)/g, "_{$1}"); // x_i → x_{i} (not inside \_ or {})
  for (let k = 0; k < 6; k++) {
    t = t
      .replace(/\^\{([^}]*)\}\^\{([^}]*)\}/g, "^{$1$2}")
      .replace(/_\{([^}]*)\}_\{([^}]*)\}/g, "_{$1$2}");
  }
  t = t.replace(/[α-ωΑ-ΩΣΠΔΦ]/g, (c) => (GREEK[c] ? GREEK[c] + " " : c));
  t = t
    .replace(/·/g, "\\cdot ").replace(/×/g, "\\times ").replace(/÷/g, "\\div ")
    .replace(/≥/g, "\\ge ").replace(/≤/g, "\\le ").replace(/≠/g, "\\ne ").replace(/≈/g, "\\approx ")
    .replace(/→/g, "\\to ").replace(/←/g, "\\leftarrow ").replace(/∂/g, "\\partial ")
    .replace(/…/g, "\\dots ").replace(/∑/g, "\\sum ").replace(/−/g, "-").replace(/∞/g, "\\infty ")
    .replace(/±/g, "\\pm ").replace(/‖/g, "\\|").replace(/√/g, "\\sqrt");
  t = t.replace(/\\sqrt\s*\(([^)]*)\)/g, "\\sqrt{$1}");
  return t;
}

export default function Tex({
  children,
  block = false,
  className,
}: {
  children: string;
  block?: boolean;
  className?: string;
}) {
  const html = useMemo(() => {
    try {
      return katex.renderToString(toTex(children), {
        throwOnError: false,
        displayMode: block,
        output: "html",
      });
    } catch {
      return null;
    }
  }, [children, block]);
  if (html == null) return <code className={className}>{children}</code>;
  return <span className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}
