'use client';

import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Activity, BrainCircuit, Database, ShieldCheck, Sparkles } from 'lucide-react';

type World = 'BRAIN' | 'ORBIT' | 'MEMORY' | 'SYNAPSE' | 'FLY LAB';
type Destination = 'BRAIN' | 'ORBIT' | 'MEMORY VAULT' | 'SYNAPSE TRACE' | 'SETTINGS';
type Props = {
  connected: boolean;
  model: string;
  checkpoint: unknown;
  memoryCount: number | null;
  traceCount: number | null;
  onOpen: (page: Destination) => void;
};
const WORLDS: { name: World; heading: string; detail: string; destination: Destination }[] = [
  { name: 'BRAIN', heading: 'One story. Many brains.', detail: 'A replaceable model reads context from a separate, owner-controlled substrate.', destination: 'BRAIN' },
  { name: 'ORBIT', heading: 'Your own cosmic orbit.', detail: 'Explore the real runtime identity and state without granting the model any new authority.', destination: 'ORBIT' },
  { name: 'MEMORY', heading: 'Keep your history.', detail: 'The memory vault is stored outside the model. Empty and disconnected states stay honest.', destination: 'MEMORY VAULT' },
  { name: 'SYNAPSE', heading: 'Follow the signal.', detail: 'Inspect recorded checkpoint and trace events, not invented internal reasoning.', destination: 'SYNAPSE TRACE' },
  { name: 'FLY LAB', heading: 'A tiny universe of connections.', detail: 'An illustrative neural constellation. It is not live FlyWire activity or measured biological data.', destination: 'SETTINGS' },
];
const NODES = [
  [10, 49], [23, 24], [27, 72], [38, 48], [45, 15], [47, 82],
  [58, 34], [61, 65], [75, 18], [79, 48], [88, 77], [94, 34],
];
const EDGES = [[0,1],[0,2],[0,3],[1,3],[1,4],[2,3],[2,5],[3,4],[3,6],[3,7],[4,6],[5,7],[6,7],[6,8],[6,9],[7,9],[7,10],[8,9],[8,11],[9,10],[9,11],[10,11]];
const VERTEX = [
  'attribute vec2 a_position;',
  'void main(){gl_Position=vec4(a_position,0.0,1.0);}',
].join('\n');
const FRAGMENT = [
  'precision mediump float;',
  'uniform vec2 u_size;',
  'uniform float u_time;',
  'uniform float u_world;',
  'void main(){',
  '  vec2 p=(gl_FragCoord.xy-0.5*u_size)/max(u_size.y,1.0);',
  '  float r=length(p);',
  '  float a=atan(p.y,p.x);',
  '  float t=u_time*0.065;',
  '  float clouds=sin(p.x*5.5+t+sin(p.y*6.0))*sin(p.y*5.0-t*0.7);',
  '  clouds+=0.45*sin(p.x*11.0-p.y*8.0+t*1.3);',
  '  float nebula=exp(-3.6*r*r)*(0.46+0.22*clouds);',
  '  float ring=exp(-110.0*pow(r-0.34-0.012*sin(a*7.0+t),2.0));',
  '  float stars=pow(max(0.0,sin(p.x*213.1)*sin(p.y*197.7)),75.0)*0.16;',
  '  vec3 violet=vec3(0.40,0.23,0.79);',
  '  vec3 teal=vec3(0.10,0.68,0.73);',
  '  vec3 rose=vec3(0.85,0.30,0.62);',
  '  vec3 accent=mix(violet,teal,step(1.5,u_world));',
  '  accent=mix(accent,rose,step(3.5,u_world));',
  '  vec3 col=vec3(0.027,0.032,0.085)+accent*max(0.0,nebula)+mix(teal,violet,0.5+0.5*sin(a*4.0))*ring*0.13;',
  '  col+=vec3(0.68,0.82,1.0)*stars;',
  '  gl_FragColor=vec4(col,1.0);',
  '}',
].join('\n');

/** Decorative WebGL only: no sensor input, model output, or biological measurements enter the shader. */
export default function CosmosWorld({ connected, model, checkpoint, memoryCount, traceCount, onOpen }: Props) {
  const [world, setWorld] = useState<World>('BRAIN');
  const [graphics, setGraphics] = useState<'checking' | 'webgl' | 'fallback'>('checking');
  const [reduced, setReduced] = useState(false);
  const canvas = useRef<HTMLCanvasElement>(null);
  const activeWorld = useRef(0);
  const selected = WORLDS.findIndex(item => item.name === world);
  const current = WORLDS[selected];
  activeWorld.current = selected;

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduced(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);

  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const gl = element.getContext('webgl', { alpha: false, antialias: false, powerPreference: 'low-power' });
    if (!gl) { setGraphics('fallback'); return; }
    let animation = 0;
    let disposed = false;
    let lastFrame = 0;
    let start = performance.now();
    const compile = (kind: number, source: string) => {
      const shader = gl.createShader(kind);
      if (!shader) return null;
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) { gl.deleteShader(shader); return null; }
      return shader;
    };
    const vertex = compile(gl.VERTEX_SHADER, VERTEX);
    const fragment = compile(gl.FRAGMENT_SHADER, FRAGMENT);
    const program = vertex && fragment ? gl.createProgram() : null;
    const buffer = gl.createBuffer();
    if (!program || !buffer || !vertex || !fragment) {
      if (vertex) gl.deleteShader(vertex);
      if (fragment) gl.deleteShader(fragment);
      if (program) gl.deleteProgram(program);
      if (buffer) gl.deleteBuffer(buffer);
      setGraphics('fallback');
      return;
    }
    gl.attachShader(program, vertex);
    gl.attachShader(program, fragment);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      gl.deleteBuffer(buffer); gl.deleteProgram(program); gl.deleteShader(vertex); gl.deleteShader(fragment);
      setGraphics('fallback');
      return;
    }
    gl.useProgram(program);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]), gl.STATIC_DRAW);
    const position = gl.getAttribLocation(program, 'a_position');
    if (position < 0) {
      gl.deleteBuffer(buffer); gl.deleteProgram(program); gl.deleteShader(vertex); gl.deleteShader(fragment);
      setGraphics('fallback');
      return;
    }
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
    const sizeUniform = gl.getUniformLocation(program, 'u_size');
    const timeUniform = gl.getUniformLocation(program, 'u_time');
    const worldUniform = gl.getUniformLocation(program, 'u_world');
    function resize() {
      if (!element || !gl || disposed) return;
      const bounds = element.getBoundingClientRect();
      const scale = Math.min(window.devicePixelRatio || 1, 1.5);
      const width = Math.min(1500, Math.max(1, Math.floor(bounds.width * scale)));
      const height = Math.min(1100, Math.max(1, Math.floor(bounds.height * scale)));
      if (element.width !== width || element.height !== height) {
        element.width = width; element.height = height;
      }
      gl.viewport(0, 0, width, height);
    }
    function render(now: number) {
      if (disposed || !gl || !element || document.hidden) return;
      if (!reduced && now - lastFrame < 40) {
        animation = requestAnimationFrame(render);
        return;
      }
      lastFrame = now;
      resize();
      gl.uniform2f(sizeUniform, element.width, element.height);
      gl.uniform1f(timeUniform, reduced ? 0 : (now - start) / 1000);
      gl.uniform1f(worldUniform, activeWorld.current);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      if (!reduced) animation = requestAnimationFrame(render);
    }
    const onVisibility = () => {
      if (document.hidden) cancelAnimationFrame(animation);
      else { start = performance.now(); animation = requestAnimationFrame(render); }
    };
    const onLost = (event: Event) => {
      event.preventDefault();
      disposed = true;
      cancelAnimationFrame(animation);
      setGraphics('fallback');
    };
    const observer = new ResizeObserver(() => {
      resize();
      if (reduced) render(performance.now());
    });
    element.addEventListener('webglcontextlost', onLost);
    document.addEventListener('visibilitychange', onVisibility);
    observer.observe(element);
    setGraphics('webgl');
    animation = requestAnimationFrame(render);
    return () => {
      disposed = true;
      cancelAnimationFrame(animation);
      observer.disconnect();
      document.removeEventListener('visibilitychange', onVisibility);
      element.removeEventListener('webglcontextlost', onLost);
      if (!gl.isContextLost()) {
        gl.deleteBuffer(buffer);
        gl.deleteProgram(program);
        gl.deleteShader(vertex);
        gl.deleteShader(fragment);
      }
    };
  }, [reduced]);

  return <section className="cosmos-world" aria-label="Cosmos five-world interface">
    <canvas className="cosmos-world-canvas" ref={canvas} aria-hidden="true" />
    <div className={'cosmos-world-ambient ' + (graphics === 'fallback' ? 'cosmos-world-fallback' : '')} aria-hidden="true" />
    <header className="cosmos-world-head">
      <div><span className="cosmos-world-eyebrow"><Sparkles size={13} /> COSMOS // IMMERSIVE INTERFACE</span>
        <h1>Explore your <em>universe.</em></h1>
        <p>Five worlds. One owner-controlled story. Visual effects are illustrative, not live neural or biological measurements.</p>
      </div>
      <span className="cosmos-world-badge" role="status">{graphics === 'webgl' ? (reduced ? 'STATIC GRAPHICS' : 'WEBGL ACTIVE') : graphics === 'fallback' ? 'STATIC GRAPHICS' : 'GRAPHICS STARTING'}</span>
    </header>
    <div className="cosmos-world-scene">
      <div className="cosmos-world-cloud" aria-hidden="true">
        <div className="cosmos-world-core" />
        <div className="cosmos-world-halo" />
        <svg className="cosmos-world-fly" viewBox="0 0 100 100" role="presentation" focusable="false">
          {EDGES.map(([from,to],index) => <line key={'e'+index} x1={NODES[from][0]} y1={NODES[from][1]} x2={NODES[to][0]} y2={NODES[to][1]} />)}
          {NODES.map(([x,y],index) => <circle key={'n'+index} cx={x} cy={y} r={index === 3 || index === 9 ? 2.2 : 1.35} />)}
        </svg>
      </div>
      <div className="cosmos-world-info" aria-live="polite">
        <span className="cosmos-world-count">WORLD 0{selected + 1} / 05</span>
        <h2>{current.heading}</h2>
        <p>{current.detail}</p>
        <button className="cosmos-world-enter" type="button" onClick={() => onOpen(current.destination)}>
          {world === 'FLY LAB' ? 'Open owner settings' : 'Open ' + current.destination.toLowerCase()} <ArrowRight size={16} />
        </button>
      </div>
    </div>
    <nav className="cosmos-world-nav" aria-label="Choose a cosmic world">
      {WORLDS.map((item,index) => <button key={item.name} type="button" aria-pressed={world === item.name} className={'cosmos-world-option ' + (world === item.name ? 'active' : '')} onClick={() => setWorld(item.name)}>
        <span className="cosmos-world-number">0{index+1}</span><span>{item.name}</span>
      </button>)}
    </nav>
    <div className="cosmos-world-readouts" aria-label="Real runtime status">
      <div><BrainCircuit size={16}/><span>Model profile</span><strong>{connected ? model : 'Not connected'}</strong></div>
      <div><Activity size={16}/><span>Checkpoint</span><strong>{checkpoint === null || checkpoint === undefined ? 'Unavailable' : String(checkpoint)}</strong></div>
      <div><Database size={16}/><span>Memory / trace</span><strong>{memoryCount === null ? '—' : memoryCount} / {traceCount === null ? '—' : traceCount}</strong></div>
      <div><ShieldCheck size={16}/><span>Authority</span><strong>Owner-controlled</strong></div>
    </div>
    <p className="cosmos-world-disclaimer">ILLUSTRATIVE GRAPHICS // ACTUAL STATUS READ FROM AUTHENTICATED COSMOS // NO AUTOMATIC TOOL AUTHORITY</p>
  </section>;
}
