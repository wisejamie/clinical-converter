"use client";

import React, { useState } from "react";

type ParsedType = any;
type FhirBundle = any;

type ConvertResponse = {
  parsed: ParsedType;
  fhir: FhirBundle;
  summary_deterministic: string;
};

const SAMPLE_HL7 = `MSH|^~\\&|InpatientSys|CommunityClinic|DownstreamSys|DestFacility|20251122135500||ADT^A01|123456|P|2.3.1
EVN|A01|20251122135500|||
PID|1||99887711^^^HOSP^MR||Johnson^Emily||19890522|F||2106-3|10 Main St^^Montreal^QC^H3Z2Y7||5145551212|||M
PV1|1|I|203^Room203^Ward2^GH|||55678^Patel^Sonia^MD|||MED||||1|A0|||||||7654321||||||||||||||||20251122135500|20251122150000
OBR|1||1111^LAB|2345-7^Glucose^LN|||||||||55678^Patel^Sonia^MD
OBX|1|NM|2345-7^Glucose^LN||7.8|mmol/L|3.6-7.7|H
OBX|2|NM|4548-4^Hemoglobin A1c^LN||6.1|%|4.0-5.6|H
OBX|3|TX|1111-1^Comment^LN||Fasting sample taken 12 hours post-midnight
`;

const TABS = [
  "Parsed HL7",
  "FHIR JSON",
  "Deterministic Summary",
  "LLM Summary",
] as const;
type Tab = (typeof TABS)[number];

export default function HomePage() {
  const [hl7Text, setHl7Text] = useState(SAMPLE_HL7);
  const [activeTab, setActiveTab] = useState<Tab>("Deterministic Summary");
  const [parsed, setParsed] = useState<ParsedType | null>(null);
  const [fhir, setFhir] = useState<FhirBundle | null>(null);
  const [summaryDeterministic, setSummaryDeterministic] = useState<
    string | null
  >(null);
  const [summaryLlm, setSummaryLlm] = useState<string | null>(null);
  const [isConverting, setIsConverting] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL;

  async function handleConvert() {
    setError(null);
    setIsConverting(true);
    setSummaryLlm(null); // clear old LLM summary when reconverting

    try {
      if (!apiBase) {
        throw new Error("API base URL is not configured.");
      }

      const res = await fetch(`${apiBase}/convert`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hl7: hl7Text }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          body.detail || `Convert request failed with status ${res.status}`
        );
      }

      const data: ConvertResponse = await res.json();
      setParsed(data.parsed);
      setFhir(data.fhir);
      setSummaryDeterministic(data.summary_deterministic);
      // Default to deterministic summary tab after convert
      setActiveTab("Deterministic Summary");
    } catch (e: any) {
      setError(e.message || "An unknown error occurred.");
    } finally {
      setIsConverting(false);
    }
  }

  async function handleLlmSummary() {
    setError(null);
    setIsSummarizing(true);

    try {
      if (!apiBase) {
        throw new Error("API base URL is not configured.");
      }
      if (!fhir) {
        throw new Error("No FHIR bundle available. Run conversion first.");
      }

      const res = await fetch(`${apiBase}/summary-llm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bundle: fhir }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          body.detail || `LLM summary request failed with status ${res.status}`
        );
      }

      const data = await res.json();
      setSummaryLlm(data.summary_llm);
      setActiveTab("LLM Summary");
    } catch (e: any) {
      setError(
        e.message || "An unknown error occurred while generating LLM summary."
      );
    } finally {
      setIsSummarizing(false);
    }
  }

  function handleLoadSample() {
    setHl7Text(SAMPLE_HL7);
  }

  function renderTabContent() {
    switch (activeTab) {
      case "Parsed HL7":
        return (
          <JsonCard
            title="Parsed HL7 structure"
            data={parsed}
            placeholder="No parsed data yet. Paste HL7 and click Convert."
          />
        );
      case "FHIR JSON":
        return (
          <JsonCard
            title="FHIR Bundle"
            data={fhir}
            placeholder="No FHIR bundle yet. Paste HL7 and click Convert."
          />
        );
      case "Deterministic Summary":
        return (
          <TextCard
            title="Deterministic Summary"
            text={summaryDeterministic}
            placeholder="No deterministic summary yet. Paste HL7 and click Convert."
          />
        );
      case "LLM Summary":
        return (
          <TextCard
            title="LLM Summary"
            text={summaryLlm}
            placeholder="No LLM summary yet. First convert, then click Generate LLM Summary."
          />
        );
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <header className="mb-8">
          <h1 className="text-3xl font-semibold tracking-tight mb-2">
            Clinical Converter – HL7 → FHIR Demo
          </h1>
          <p className="text-sm text-slate-300 max-w-2xl">
            Paste or edit an HL7 v2 message on the left, then convert it into a
            FHIR R4 Bundle and view deterministic and LLM-generated summaries.
            Backed by a FastAPI service running on Render.
          </p>
        </header>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Left: HL7 input */}
          <section className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium">HL7 Input</h2>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleLoadSample}
                  className="rounded-md border border-slate-600 px-3 py-1 text-xs hover:bg-slate-800"
                >
                  Load sample ADT
                </button>
              </div>
            </div>
            <textarea
              className="h-[340px] w-full resize-none rounded-lg border border-slate-700 bg-slate-900/70 p-3 text-sm font-mono text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
              value={hl7Text}
              onChange={(e) => setHl7Text(e.target.value)}
              spellCheck={false}
            />

            {error && (
              <div className="rounded-md border border-red-500 bg-red-950/40 px-3 py-2 text-xs text-red-200">
                {error}
              </div>
            )}

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleConvert}
                disabled={isConverting}
                className="inline-flex items-center rounded-md bg-sky-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-sky-400 disabled:opacity-60"
              >
                {isConverting ? "Converting…" : "Convert to FHIR"}
              </button>

              <button
                type="button"
                onClick={handleLlmSummary}
                disabled={isSummarizing || !fhir}
                className="inline-flex items-center rounded-md border border-sky-500 px-4 py-2 text-sm font-medium text-sky-200 hover:bg-sky-900 disabled:opacity-40"
              >
                {isSummarizing
                  ? "Generating LLM Summary…"
                  : "Generate LLM Summary"}
              </button>
            </div>
          </section>

          {/* Right: Results */}
          <section className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium">Results</h2>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-900/70">
              <div className="flex border-b border-slate-800 text-xs">
                {TABS.map((tab) => (
                  <button
                    key={tab}
                    type="button"
                    onClick={() => setActiveTab(tab)}
                    className={`flex-1 px-3 py-2 text-center ${
                      activeTab === tab
                        ? "bg-slate-900 text-sky-300 border-b-2 border-sky-500"
                        : "text-slate-400 hover:bg-slate-900/60"
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              <div className="p-3 text-xs">{renderTabContent()}</div>
            </div>
          </section>
        </div>

        <footer className="mt-10 text-xs text-slate-500">
          Backend: <code>FastAPI</code> on Render · Frontend:{" "}
          <code>Next.js + Tailwind</code> on Vercel
        </footer>
      </div>
    </main>
  );
}

type JsonCardProps = {
  title: string;
  data: any;
  placeholder: string;
};

function JsonCard({ title, data, placeholder }: JsonCardProps) {
  const pretty = data ? JSON.stringify(data, null, 2) : null;

  const handleCopy = () => {
    if (!pretty) return;
    navigator.clipboard.writeText(pretty).catch(() => {});
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="font-medium text-slate-200">{title}</span>
        <button
          type="button"
          onClick={handleCopy}
          disabled={!pretty}
          className="rounded-md border border-slate-600 px-2 py-1 text-[10px] text-slate-200 hover:bg-slate-800 disabled:opacity-40"
        >
          Copy JSON
        </button>
      </div>
      <pre className="max-h-[280px] overflow-auto rounded-md bg-slate-950/80 p-2 text-[11px] leading-snug text-slate-100">
        {pretty || placeholder}
      </pre>
    </div>
  );
}

type TextCardProps = {
  title: string;
  text: string | null;
  placeholder: string;
};

function TextCard({ title, text, placeholder }: TextCardProps) {
  const handleCopy = () => {
    if (!text) return;
    navigator.clipboard.writeText(text).catch(() => {});
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="font-medium text-slate-200">{title}</span>
        <button
          type="button"
          onClick={handleCopy}
          disabled={!text}
          className="rounded-md border border-slate-600 px-2 py-1 text-[10px] text-slate-200 hover:bg-slate-800 disabled:opacity-40"
        >
          Copy text
        </button>
      </div>
      <div className="max-h-[280px] overflow-auto rounded-md bg-slate-950/80 p-3 text-[11px] leading-snug text-slate-100 whitespace-pre-wrap">
        {text || placeholder}
      </div>
    </div>
  );
}
