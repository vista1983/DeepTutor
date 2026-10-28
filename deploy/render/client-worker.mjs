// Server-only Site MCP bridge. Publish as an owner-private Site with capability "mcp".
// Configure DEEPTUTOR_BASE_URL and DEEPTUTOR_MCP_TOKEN as hosted runtime secrets.
import tools from './client-tools.json';

const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
});

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (path === '/') {
      return new Response(`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DeepTutor 学习助手</title><style>body{font:18px/1.8 system-ui;max-width:720px;margin:12vh auto;padding:24px;background:#f5f7fb;color:#17243a}h1{font-size:36px}p{color:#43516a}</style><h1>DeepTutor 学习助手</h1><p>在客户端选择本插件，即可提交学习问题、生成练习、开展研究并查看任务进度。</p><p>首次使用需在 DeepTutor 网页的 Settings → Providers 配置并测试模型。服务在线不代表模型已就绪。</p><p>本插件仅用于所有者的私人学习空间。</p></html>`, {headers:{'content-type':'text/html; charset=utf-8'}});
    }
    if (path !== '/mcp' || request.method !== 'POST') return json({error:'Not found'},404);
    const bytes = await request.arrayBuffer();
    if (bytes.byteLength > 131072) return json({error:'Request too large'},413);
    let body;
    try { body = JSON.parse(new TextDecoder().decode(bytes)); }
    catch { return json({jsonrpc:'2.0',id:null,error:{code:-32700,message:'Parse error'}}); }
    if (!body || typeof body !== 'object' || body.jsonrpc !== '2.0') return json({error:'Invalid request'},400);
    const envelope = {jsonrpc:'2.0',id:body.id ?? null};
    if (body.method === 'server/discover') return json({...envelope,result:{supportedVersions:['2026-07-28'],capabilities:{tools:{}}}});
    if (body.method === 'tools/list') return json({...envelope,result:{tools}});
    if (body.method === 'ping') return json({...envelope,result:{}});
    if (body.method !== 'tools/call') return json({...envelope,error:{code:-32601,message:'Method not found'}});
    if (!request.headers.get('oai-authenticated-user-id')) return json({error:'Authentication required'},401);
    if (!tools.some(t=>t.name===body.params?.name)) return json({...envelope,error:{code:-32602,message:'Unknown tool'}});
    const failure = message => json({...envelope,result:{isError:true,content:[{type:'text',text:message}]}});
    if (!env.DEEPTUTOR_BASE_URL || !env.DEEPTUTOR_MCP_TOKEN) return failure('DeepTutor 云端连接尚未配置完成，当前不能执行任务。');
    try {
      const base = new URL(env.DEEPTUTOR_BASE_URL);
      if (base.protocol !== 'https:' || base.username || base.password) return failure('DeepTutor 服务地址配置无效。');
      const upstream = await fetch(new URL('/api/client-mcp',base), {
        method:'POST', headers:{'content-type':'application/json',authorization:`Bearer ${env.DEEPTUTOR_MCP_TOKEN}`},
        body:JSON.stringify(body), redirect:'error', signal:AbortSignal.timeout(25000),
      });
      if (!upstream.ok) return failure('DeepTutor 服务暂不可用或连接认证失败，请检查云端服务状态。');
      return json(await upstream.json());
    } catch { return failure('DeepTutor 连接超时或响应异常。请稍后检查任务状态，避免重复提交。'); }
  },
};
