"use client";

import React, { useState, useCallback, useRef, useEffect } from "react";
import ReactFlow, {
  addEdge,
  useNodesState,
  useEdgesState,
  Connection,
  Edge,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  ReactFlowInstance,
} from "reactflow";
import { CustomAgentNode, CustomAgentEdge, NodeType } from "./types";
import { nodeTypes } from "./CustomNodes";
import { NodePalette } from "./NodePalette";
import { NodeInspector } from "./NodeInspector";
import { DEFAULT_TEMPLATES } from "./defaultGraphs";
import { generatePythonCode } from "./codeGen";
import {
  runGraphSimulation,
  SimulationResult,
  convertTraceEventToSimulation,
  createDemoReplayTrace,
} from "./simulator";
import { TraceReplayBar } from "./TraceReplayBar";
import { LatencyWaterfall } from "./LatencyWaterfall";
import { StateSnapshotViewer } from "./StateSnapshotViewer";

export default function AgentCanvas({
  initialTemplateId,
  initialTraceToReplay,
  onNavigateToTracing,
}: {
  initialTemplateId?: string;
  initialTraceToReplay?: any;
  onNavigateToTracing?: (traceId: string) => void;
}) {
  const initialTemplate =
    DEFAULT_TEMPLATES.find((t) => t.id === initialTemplateId) || DEFAULT_TEMPLATES[0];

  const [nodes, setNodes, onNodesChange] = useNodesState<CustomAgentNode["data"]>(
    initialTemplate.nodes
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialTemplate.edges);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(true);
  const [activeWorkflowName, setActiveWorkflowName] = useState(initialTemplate.name);

  // Modals & Panels
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
  const [showSimModal, setShowSimModal] = useState(false);
  const [testQuery, setTestQuery] = useState("How does dynavec achieve sub-10ms vector search in AWS S3?");

  // Visual Trace Replay State
  const [replayTrace, setReplayTrace] = useState<SimulationResult | null>(null);
  const [replayStepIndex, setReplayStepIndex] = useState(0);
  const [isReplaying, setIsReplaying] = useState(false);
  const [replaySpeed, setReplaySpeed] = useState(1);
  const [showWaterfall, setShowWaterfall] = useState(false);
  const [showSnapshotViewer, setShowSnapshotViewer] = useState(false);

  const [showCodeModal, setShowCodeModal] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);

  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  // Automatically start replay if an external trace was passed
  useEffect(() => {
    if (initialTraceToReplay) {
      const converted = convertTraceEventToSimulation(initialTraceToReplay);
      setReplayTrace(converted);
      setReplayStepIndex(0);
      setIsReplaying(true);
      setShowWaterfall(true);
    }
  }, [initialTraceToReplay]);

  // Replay playback timer
  useEffect(() => {
    if (!isReplaying || !replayTrace) return;
    const intervalMs = Math.max(350, Math.round(1200 / replaySpeed));
    const timer = setInterval(() => {
      setReplayStepIndex((prev) => {
        if (prev >= replayTrace.nodeTraces.length - 1) {
          setIsReplaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, intervalMs);
    return () => clearInterval(timer);
  }, [isReplaying, replayTrace, replaySpeed]);

  // Synchronize graph nodes during replay
  useEffect(() => {
    if (!replayTrace) return;
    const currentStep = replayTrace.nodeTraces[replayStepIndex];
    if (!currentStep) return;

    const visitedIds = new Set(
      replayTrace.nodeTraces.slice(0, replayStepIndex).map((s) => s.nodeId)
    );

    setNodes((nds) =>
      nds.map((n) => {
        if (n.id === currentStep.nodeId) {
          return {
            ...n,
            data: {
              ...n.data,
              status: "running",
              executionTimeMs: currentStep.latencyMs,
              lastOutput: currentStep.output,
            },
          };
        } else if (visitedIds.has(n.id)) {
          const past = replayTrace.nodeTraces.find((s) => s.nodeId === n.id);
          return {
            ...n,
            data: {
              ...n.data,
              status: "success",
              executionTimeMs: past?.latencyMs,
              lastOutput: past?.output,
            },
          };
        } else {
          return {
            ...n,
            data: {
              ...n.data,
              status: "idle",
            },
          };
        }
      })
    );
  }, [replayStepIndex, replayTrace, setNodes]);

  // Handle Connections
  const onConnect = useCallback(
    (params: Connection | Edge) => {
      setEdges((eds) =>
        addEdge(
          {
            ...params,
            animated: true,
            style: { stroke: "#e8623b", strokeWidth: 2 },
          },
          eds
        )
      );
    },
    [setEdges]
  );

  // Select Node
  const onNodeClick = useCallback((_: React.MouseEvent, node: CustomAgentNode) => {
    setSelectedNodeId(node.id);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  // Update Node Config
  const handleUpdateConfig = (nodeId: string, updates: Partial<CustomAgentNode["data"]>) => {
    setNodes((nds) =>
      nds.map((n) => {
        if (n.id === nodeId) {
          return {
            ...n,
            data: {
              ...n.data,
              ...updates,
            },
          };
        }
        return n;
      })
    );
  };

  // Delete Node
  const handleDeleteNode = (nodeId: string) => {
    setNodes((nds) => nds.filter((n) => n.id !== nodeId));
    setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
    if (selectedNodeId === nodeId) setSelectedNodeId(null);
  };

  // Duplicate Node
  const handleDuplicateNode = (nodeId: string) => {
    const target = nodes.find((n) => n.id === nodeId);
    if (!target) return;

    const newId = `node-${target.data.type}-${Date.now().toString(36)}`;
    const newNode: CustomAgentNode = {
      ...target,
      id: newId,
      position: {
        x: target.position.x + 40,
        y: target.position.y + 40,
      },
      data: {
        ...target.data,
        label: `${target.data.label} (Copy)`,
        status: "idle",
        lastOutput: undefined,
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setSelectedNodeId(newId);
  };

  // Add Node from Palette
  const handleAddNode = (
    type: NodeType,
    label: string,
    description: string,
    defaultConfig: Record<string, any>
  ) => {
    const newId = `node-${type}-${Date.now().toString(36)}`;
    const position = reactFlowInstance
      ? reactFlowInstance.project({
          x: (reactFlowWrapper.current?.clientWidth || 800) / 2 - 100,
          y: (reactFlowWrapper.current?.clientHeight || 600) / 2 - 50,
        })
      : { x: 300, y: 200 };

    const newNode: CustomAgentNode = {
      id: newId,
      type: "agentNode",
      position,
      data: {
        label,
        type,
        description,
        config: defaultConfig,
        status: "idle",
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setSelectedNodeId(newId);
  };

  // Drag & Drop on Canvas
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      if (!reactFlowWrapper.current || !reactFlowInstance) return;

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const rawData = event.dataTransfer.getData("application/reactflow");
      if (!rawData) return;

      const item = JSON.parse(rawData);
      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      const newId = `node-${item.type}-${Date.now().toString(36)}`;
      const newNode: CustomAgentNode = {
        id: newId,
        type: "agentNode",
        position,
        data: {
          label: item.label,
          type: item.type,
          description: item.description,
          config: item.defaultConfig,
          status: "idle",
        },
      };

      setNodes((nds) => [...nds, newNode]);
      setSelectedNodeId(newId);
    },
    [reactFlowInstance, setNodes]
  );

  // Load Template
  const handleLoadTemplate = (templateId: string) => {
    const tmpl = DEFAULT_TEMPLATES.find((t) => t.id === templateId);
    if (!tmpl) return;
    setNodes(tmpl.nodes);
    setEdges(tmpl.edges);
    setActiveWorkflowName(tmpl.name);
    setSelectedNodeId(null);
    setSimulationResult(null);
    setTimeout(() => {
      reactFlowInstance?.fitView({ padding: 0.2 });
    }, 50);
  };

  // Run Test Simulation
  const handleRunSimulation = async () => {
    setIsSimulating(true);
    setShowSimModal(true);

    const onNodeStateChange = (nodeId: string, status: any, extraData?: any) => {
      setNodes((nds) =>
        nds.map((n) => {
          if (n.id === nodeId) {
            return {
              ...n,
              data: {
                ...n.data,
                status,
                ...(extraData || {}),
              },
            };
          }
          return n;
        })
      );
    };

    try {
      const result = await runGraphSimulation(nodes, edges, testQuery, onNodeStateChange);
      setSimulationResult(result);
    } catch (e: any) {
      console.error("Simulation error", e);
    } finally {
      setIsSimulating(false);
    }
  };

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || null;
  const pythonCode = generatePythonCode(activeWorkflowName, nodes, edges);

  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden bg-bg">
      {/* Top Studio Control Bar */}
      <div className="h-14 border-b border-line bg-surface/90 backdrop-blur px-4 flex items-center justify-between z-20 shrink-0">
        {/* Left: Workflow title & selector */}
        <div className="flex items-center gap-3">
          <span className="w-6 h-6 rounded bg-accent-soft text-accent flex items-center justify-center font-mono font-bold text-xs">AG</span>
          <div>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={activeWorkflowName}
                onChange={(e) => setActiveWorkflowName(e.target.value)}
                className="font-bold text-sm text-ink bg-transparent border-b border-transparent hover:border-line focus:border-accent focus:outline-none"
              />
              <span className="font-mono text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 font-semibold">
                ● Ready
              </span>
            </div>
            <span className="text-[11px] text-faint font-mono">
              {nodes.length} nodes · {edges.length} edges
            </span>
          </div>

          <div className="h-5 w-[1px] bg-line mx-2 hidden sm:block" />

          {/* Template presets */}
          <div className="hidden md:flex items-center gap-1.5">
            <span className="text-[11px] font-mono text-muted">Template:</span>
            <select
              onChange={(e) => handleLoadTemplate(e.target.value)}
              className="text-xs bg-bg border border-line rounded px-2 py-1 text-ink focus:border-accent"
              defaultValue={initialTemplate.id}
            >
              {DEFAULT_TEMPLATES.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          {/* Node Palette toggle for mobile */}
          <button
            type="button"
            onClick={() => setPaletteOpen(!paletteOpen)}
            className="md:hidden py-1.5 px-2.5 rounded text-xs font-mono border border-line bg-bg text-ink"
          >
            Components
          </button>

          <button
            type="button"
            onClick={() => {
              setNodes((nds) => nds.map((n) => ({ ...n, data: { ...n.data, status: "idle" } })));
              reactFlowInstance?.fitView({ padding: 0.2 });
            }}
            className="py-1.5 px-2.5 rounded text-xs font-mono border border-line bg-surface text-muted hover:text-ink hover:bg-bg transition-colors"
            title="Reset View & States"
          >
            Fit View
          </button>

          <button
            type="button"
            onClick={() => setShowCodeModal(true)}
            className="py-1.5 px-3 rounded text-xs font-mono font-medium border border-line bg-surface hover:bg-bg text-ink flex items-center gap-1.5 transition-colors"
          >
            <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-accent-soft text-accent">PYTHON</span>
            <span>Export Python</span>
          </button>

          <button
            type="button"
            onClick={() => {
              if (replayTrace) {
                setIsReplaying(!isReplaying);
              } else {
                const demo = simulationResult || createDemoReplayTrace();
                setReplayTrace(demo);
                setReplayStepIndex(0);
                setIsReplaying(true);
                setShowWaterfall(true);
              }
            }}
            className="py-1.5 px-3 rounded text-xs font-mono font-medium border border-line bg-surface hover:bg-bg text-ink flex items-center gap-1.5 transition-colors"
            title="Replay trace step-by-step on canvas"
          >
            <span className="font-mono text-xs">&laquo; Step</span>
            <span>{replayTrace ? (isReplaying ? "Pause" : "Resume Replay") : "Visual Replay"}</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setShowSimModal(true);
              if (!simulationResult) handleRunSimulation();
            }}
            disabled={isSimulating}
            className="py-1.5 px-4 rounded text-xs font-mono font-semibold bg-accent text-white hover:bg-accent/90 shadow-sm flex items-center gap-1.5 transition-all active:scale-95"
          >
            {isSimulating ? (
              <>
                <span className="w-3 h-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
                <span>Executing...</span>
              </>
            ) : (
              <>
                <span className="font-mono text-xs">&#9654; Run</span>
                <span>Test Run</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Studio Area */}
      <div className="flex-1 relative flex" ref={reactFlowWrapper}>
        {/* Left Palette */}
        <NodePalette
          isOpen={paletteOpen}
          onToggle={() => setPaletteOpen(!paletteOpen)}
          onAddNode={handleAddNode}
        />

        {/* Canvas Area */}
        <div className={`flex-1 h-full transition-all duration-200 ${paletteOpen ? "lg:ml-80" : "lg:ml-12"}`}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            defaultEdgeOptions={{
              animated: true,
              style: { stroke: "#e8623b", strokeWidth: 2 },
            }}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={16}
              size={1}
              color="var(--color-line)"
            />
            <Controls className="!bg-surface !border-line shadow-lg" />
            <MiniMap
              nodeStrokeColor="var(--color-accent)"
              nodeColor="var(--color-surface)"
              nodeBorderRadius={6}
              maskColor="rgba(0, 0, 0, 0.4)"
              style={{ bottom: 20, right: 20 }}
            />
          </ReactFlow>

          {/* Replay Controls & Waterfall Overlays */}
          {replayTrace && (
            <>
              <TraceReplayBar
                trace={replayTrace}
                currentStepIndex={replayStepIndex}
                onStepChange={(idx) => {
                  setReplayStepIndex(idx);
                  setIsReplaying(false);
                }}
                isPlaying={isReplaying}
                onTogglePlay={() => setIsReplaying(!isReplaying)}
                speed={replaySpeed}
                onSpeedChange={setReplaySpeed}
                onCloseReplay={() => {
                  setReplayTrace(null);
                  setIsReplaying(false);
                  setShowWaterfall(false);
                  setShowSnapshotViewer(false);
                  setNodes((nds) => nds.map((n) => ({ ...n, data: { ...n.data, status: "idle" } })));
                }}
                onToggleWaterfall={() => setShowWaterfall(!showWaterfall)}
                showWaterfall={showWaterfall}
              />

              {showWaterfall && (
                <LatencyWaterfall
                  trace={replayTrace}
                  currentStepIndex={replayStepIndex}
                  onSelectStep={(idx) => {
                    setReplayStepIndex(idx);
                    setIsReplaying(false);
                  }}
                  onClose={() => setShowWaterfall(false)}
                />
              )}

              {showSnapshotViewer && replayTrace.nodeTraces[replayStepIndex] && (
                <StateSnapshotViewer
                  step={replayTrace.nodeTraces[replayStepIndex]}
                  onClose={() => setShowSnapshotViewer(false)}
                />
              )}
            </>
          )}
        </div>

        {/* Right Inspector Drawer */}
        {selectedNode && (
          <NodeInspector
            node={selectedNode}
            onUpdateConfig={handleUpdateConfig}
            onDeleteNode={handleDeleteNode}
            onDuplicateNode={handleDuplicateNode}
            onClose={() => setSelectedNodeId(null)}
          />
        )}
      </div>

      {/* Test Execution & Simulation Modal */}
      {showSimModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface border border-line rounded-xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-line flex items-center justify-between bg-bg/50">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-accent font-bold">&rarr;</span>
                <h3 className="font-bold text-sm text-ink font-mono">
                  Agent Execution & Simulation
                </h3>
              </div>
              <button
                onClick={() => setShowSimModal(false)}
                className="text-muted hover:text-ink p-1 rounded-md hover:bg-bg transition-colors cursor-pointer"
                aria-label="Close modal"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-4 space-y-4 overflow-y-auto flex-1">
              <div>
                <label className="block text-[11px] font-mono text-muted mb-1.5">
                  Test Inbound Query / Prompt:
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={testQuery}
                    onChange={(e) => setTestQuery(e.target.value)}
                    placeholder="Enter query to test workflow..."
                    className="flex-1 text-xs bg-bg border border-line rounded-lg px-3 py-2 text-ink focus:border-accent"
                  />
                  <button
                    type="button"
                    disabled={isSimulating}
                    onClick={handleRunSimulation}
                    className="py-2 px-4 rounded-lg text-xs font-mono font-semibold bg-accent text-white hover:bg-accent/90 disabled:opacity-50"
                  >
                    {isSimulating ? "Running..." : "Run"}
                  </button>
                </div>
              </div>

              {/* Sample Prompts */}
              <div className="flex flex-wrap gap-1.5 items-center">
                <span className="text-[10px] font-mono text-faint">Try sample:</span>
                {[
                  "How does dynavec achieve sub-10ms vector search?",
                  "Show account billing status and API quota",
                  "Explain zero-copy parquet parsing",
                ].map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => setTestQuery(q)}
                    className="text-[10px] font-mono px-2 py-0.5 rounded bg-bg text-muted hover:text-ink border border-line"
                  >
                    {q}
                  </button>
                ))}
              </div>

              {/* Result State */}
              {simulationResult && (
                <div className="space-y-4 pt-3 border-t border-line">
                  {/* KPI Bar */}
                  <div className="grid grid-cols-4 gap-2">
                    <div className="bg-bg border border-line rounded p-2.5 text-center">
                      <span className="block text-[10px] font-mono text-faint">Status</span>
                      <span className="font-bold text-xs text-emerald-500 font-mono">Completed</span>
                    </div>
                    <div className="bg-bg border border-line rounded p-2.5 text-center">
                      <span className="block text-[10px] font-mono text-faint">Total Latency</span>
                      <span className="font-bold text-xs text-ink font-mono">{simulationResult.totalLatencyMs}ms</span>
                    </div>
                    <div className="bg-bg border border-line rounded p-2.5 text-center">
                      <span className="block text-[10px] font-mono text-faint">Tokens</span>
                      <span className="font-bold text-xs text-ink font-mono">{simulationResult.tokensUsed}</span>
                    </div>
                    <div className="bg-bg border border-line rounded p-2.5 text-center">
                      <span className="block text-[10px] font-mono text-faint">Est. Cost</span>
                      <span className="font-bold text-xs text-emerald-500 font-mono">${simulationResult.costUsd.toFixed(4)}</span>
                    </div>
                  </div>

                  {/* Output Preview */}
                  <div>
                    <label className="block text-[11px] font-mono text-muted mb-1">
                      Final Output:
                    </label>
                    <div className="bg-bg border border-line rounded-lg p-3 text-xs text-ink leading-relaxed font-sans">
                      {simulationResult.output}
                    </div>
                  </div>

                  {/* Node Execution Breakdown */}
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-[11px] font-mono text-muted">
                        Node Execution Trace Breakdown:
                      </label>
                      <span className="text-[10px] font-mono text-faint">
                        Trace ID: {simulationResult.traceId}
                      </span>
                    </div>
                    <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                      {simulationResult.nodeTraces.map((tr, i) => (
                        <div
                          key={i}
                          className="flex items-center justify-between p-2 rounded bg-bg/80 border border-line text-xs font-mono"
                        >
                          <div className="flex items-center gap-2">
                            <svg className="w-3 h-3 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                            </svg>
                            <span className="font-semibold text-ink">{tr.nodeLabel}</span>
                            <span className="text-[10px] text-faint">({tr.type})</span>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-accent">{tr.latencyMs}ms</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="p-3 border-t border-line bg-bg/50 flex justify-between items-center">
              {simulationResult && onNavigateToTracing && (
                <button
                  type="button"
                  onClick={() => {
                    setShowSimModal(false);
                    onNavigateToTracing(simulationResult.traceId);
                  }}
                  className="text-xs font-mono text-accent hover:underline flex items-center gap-1"
                >
                  Inspect in Tracing Dashboard →
                </button>
              )}
              <div className="flex items-center gap-2 ml-auto">
                {simulationResult && (
                  <button
                    type="button"
                    onClick={() => {
                      setShowSimModal(false);
                      setReplayTrace(simulationResult);
                      setReplayStepIndex(0);
                      setIsReplaying(true);
                      setShowWaterfall(true);
                    }}
                    className="py-1.5 px-3.5 rounded text-xs font-mono font-semibold bg-accent text-white hover:bg-accent/90 shadow-sm flex items-center gap-1.5 transition-all active:scale-95"
                  >
                    <span className="font-mono text-xs">Replay Execution on Canvas</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setShowSimModal(false)}
                  className="py-1.5 px-4 rounded text-xs font-mono border border-line bg-surface text-ink hover:bg-bg transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Python Code Export Modal */}
      {showCodeModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface border border-line rounded-xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-line flex items-center justify-between bg-bg/50">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold px-2 py-1 rounded bg-accent-soft text-accent">PYTHON DAG</span>
                <div>
                  <h3 className="font-bold text-sm text-ink font-mono">
                    dynavec.agents Python Export
                  </h3>
                  <p className="text-[11px] text-faint">
                    Drop directly into your Python backend or FastAPI service.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowCodeModal(false)}
                className="text-muted hover:text-ink p-1 rounded-md hover:bg-bg transition-colors cursor-pointer"
                aria-label="Close code modal"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-4 overflow-y-auto flex-1 bg-[#121214]">
              <pre className="font-mono text-xs text-[#e6edf3] leading-relaxed overflow-x-auto whitespace-pre">
                {pythonCode}
              </pre>
            </div>

            <div className="p-3 border-t border-line bg-bg/50 flex items-center justify-between">
              <span className="text-[11px] font-mono text-faint">
                Requires: dynavec &gt;= 0.2.0
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(pythonCode);
                    setCopiedCode(true);
                    setTimeout(() => setCopiedCode(false), 2000);
                  }}
                  className="py-1.5 px-4 rounded text-xs font-mono font-medium bg-accent text-white hover:bg-accent/90 transition-all flex items-center gap-1.5 cursor-pointer shadow-sm"
                >
                  {copiedCode ? (
                    <>
                      <svg className="w-3 h-3 text-white shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>Copied</span>
                    </>
                  ) : (
                    <span>Copy Code</span>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const blob = new Blob([pythonCode], { type: "text/x-python" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `${activeWorkflowName.toLowerCase().replace(/[^a-z0-9]/g, "_")}_agent.py`;
                    a.click();
                  }}
                  className="py-1.5 px-3 rounded text-xs font-mono border border-line bg-surface text-ink hover:bg-bg transition-colors"
                >
                  Download .py
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
