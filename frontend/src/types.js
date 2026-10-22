// Mirrors backend/app/schemas.py — keep in sync (JSDoc only, for editor hints).
/**
 * @typedef {'positive'|'negative'|'mixed'|'neutral'|'unknown'} Effect
 * @typedef {{id:string,label:string,type:string,sector?:string|null,effect:Effect}} Node
 * @typedef {{beta?:number,t_stat?:number,n?:number,lag_days?:number,ci_low?:number,ci_high?:number,stability?:string,note?:string}} EdgeStats
 * @typedef {{id:string,source:string,target:string,relationship:string,sign:-1|0|1,weight:number,
 *   evidence_type:'domain_rule'|'news_evidence'|'llm_inferred'|'quant_verified',
 *   verification_status:string,horizon:string,explanation:string,assumptions:string[],
 *   evidence:{source_type:string,text:string,url?:string|null}[],stats?:EdgeStats|null}} Edge
 * @typedef {{id:string,node_ids:string[],edge_ids:string[],strength:number,terminal_effect:Effect,
 *   horizon:string,explanation:string,uncertainty:string}} ImpactPath
 * @typedef {{mode:'live'|'fallback'|'mock',event:object,nodes:Node[],edges:Edge[],paths:ImpactPath[],
 *   sectors:{sector:string,exposure:string,reason:string,confidence:string}[],warnings:string[],meta:object}} AnalyzeResponse
 * @typedef {{orders:Object<string,number>,layers:{order:number,name:string,nodes:{id:string,label:string}[]}[],
 *   best_paths:{target:string,label:string,node_ids:string[],strength:number}[],
 *   influence:{id:string,label:string,sector?:string,score:number,betweenness:number,pagerank:number}[],
 *   hierarchy:{group:string,strength:number,effect:Effect,sectors:{sector:string,strength:number,effect:Effect,nodes:string[]}[]}[],
 *   hierarchy_problems:string[]}} GraphAnalysis  // lives in response.meta.graph_analysis (optional)
 * @typedef {{node_id:string,label:string,level:'alert'|'watch'|'none',negative:number,positive:number,mixed:number,direct:number,
 *   hits:number,simulated_hits:number,score:number,trend:'rising'|'steady'|'easing'|null,reason:string,last_ts:string,
 *   stories:{ts:string,headline:string,effect:string,simulated:boolean}[],drivers:{node:string,shock_sign:-1|1,count:number}[]}} StarSignal
 *   // GET /api/recurrence -> {window_days,thresholds,alerts:string[],watch:string[],nodes:Object<string,StarSignal>}
 * @typedef {{available:boolean,reason?:string,caveat:string,method?:string,driver?:object,date_range?:{start:string,end:string},
 *   targets?:{node_id:string,label:string,ticker:string,predicted:'up'|'down'|'unclear',n:number,agrees:boolean|null,leans:string|null,
 *   hit_rate:object|null,stats:object|null,last_episodes:{date:string,driver_move_pct:number,returns:object}[],note?:string}[],
 *   skipped?:{node_id:string,reason:string}[],size_comparison?:object}} Backtest  // POST /api/backtest
 */
export {}
