import React from "react";
import {
  AbsoluteFill, Audio, Composition, Easing, Img, OffthreadVideo,
  Sequence, interpolate, registerRoot, staticFile, useCurrentFrame,
  useVideoConfig,
} from "remotion";

const P = {bg:"#07111d", white:"#edf5fc", muted:"#a1b8c9",gold:"#ffd36c"};
const example = {fps:30,width:1920,height:1080,durationInFrames:90,demo:true,voiceover:null,
  scenes:[{sceneId:"S01",durationInFrames:90,kind:"graphic",title:"Demo",
    narration:"Dokumentarischer Test ohne echte Quellen.",label:"OFFLINE DEMO",source:""}]};
const excerpt = (text, n=18) => String(text||"").split(/\s+/).filter(Boolean).slice(0,n).join(" ");

const Graphic = ({scene}) => <AbsoluteFill style={{background:"linear-gradient(130deg,#07111d,#17354d 65%,#081722)"}}>
  <div style={{position:"absolute",left:85,top:110,width:1200,height:700,
    border:"2px solid #3d6078",borderRadius:380,opacity:.43}}/>
  <div style={{position:"absolute",right:85,bottom:150,width:600,height:500,
    border:"2px solid #64869e",transform:"rotate(23deg)",opacity:.5}}/>
  <div style={{position:"absolute",left:100,top:280,color:P.white,fontSize:88,
    fontWeight:820,lineHeight:1.12,maxWidth:1300}}>{scene.title}</div>
  <div style={{position:"absolute",left:100,top:190,color:P.gold,
    fontSize:29,letterSpacing:6,fontWeight:800}}>DOKU VISUAL AGENT</div>
</AbsoluteFill>;

const Chart = ({scene}) => {
  const rows=scene.chart?.values??[];
  const max=Math.max(1,...rows.map(v=>v.value));
  return <AbsoluteFill style={{background:P.bg,color:P.white,padding:"90px 120px",boxSizing:"border-box"}}>
    <div style={{fontSize:64,fontWeight:800,marginBottom:60}}>{scene.chart?.title||scene.title}</div>
    <div style={{display:"flex",alignItems:"flex-end",gap:30,height:570,
      borderBottom:"3px solid #637c94"}}>
      {rows.map((v,i)=><div key={i} style={{flex:1,textAlign:"center"}}>
        <div style={{fontSize:24,marginBottom:16,fontWeight:800}}>
          {v.value.toLocaleString("de-DE")} {scene.chart.unit||""}</div>
        <div style={{height:Math.round(v.value/max*420),
          background:"linear-gradient(#ffdf87,#be8139)",borderRadius:"8px 8px 0 0"}}/>
        <div style={{fontSize:23,paddingTop:15}}>{v.label}</div>
      </div>)}
    </div>
    <div style={{fontSize:18,color:P.muted,marginTop:52,overflowWrap:"anywhere"}}>
      Quelle: {scene.chart?.source_url}</div>
  </AbsoluteFill>;
};

const Shot=({scene,demo})=>{
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  const progress=Math.min(1,frame/Math.max(1,scene.durationInFrames));
  const zoom=interpolate(progress,[0,1],[1.015,1.075],
    {easing:Easing.inOut(Easing.quad)});
  const opacity=interpolate(frame,[0,Math.max(1,Math.round(fps*.4))],
    [0,1],{extrapolateRight:"clamp"});
  const background={width:"100%",height:"100%",objectFit:"cover",
    transform:"scale("+zoom+")"};
  return <AbsoluteFill style={{background:P.bg,color:P.white}}>
    {scene.kind==="graphic"&&<Graphic scene={scene}/>}
    {scene.kind==="chart"&&<Chart scene={scene}/>}
    {scene.kind==="image"&&<Img src={staticFile(scene.asset)} style={background}/>}
    {scene.kind==="video"&&<OffthreadVideo src={staticFile(scene.asset)} muted
      style={{width:"100%",height:"100%",objectFit:"cover"}}/>}
    {scene.kind!=="chart"&&<AbsoluteFill style={{
      background:"linear-gradient(90deg,rgba(0,0,0,.76),transparent 80%),"+
        "linear-gradient(0deg,rgba(0,0,0,.88),transparent 52%)"}}/>}
    <div style={{position:"absolute",left:90,top:65,display:"flex",alignItems:"center",gap:16}}>
      <div style={{width:12,height:36,background:P.gold}}/>
      <span style={{fontSize:29,fontWeight:850,letterSpacing:3}}>
        WISSENSDOKU <span style={{opacity:.6}}> / {scene.sceneId}</span>
      </span>
    </div>
    <div style={{position:"absolute",bottom:120,left:90,right:95,fontSize:52,
      maxWidth:1500,lineHeight:1.19,fontWeight:740,
      textShadow:"0 3px 14px #000",opacity}}>{excerpt(scene.narration)}</div>
    <div style={{position:"absolute",bottom:42,left:90,fontSize:20,fontWeight:800,
      color:P.gold,letterSpacing:2}}>{demo?
        "OFFLINE DEMO / NICHT ZUR VERÖFFENTLICHUNG":scene.label}</div>
    {scene.source&&<div style={{position:"absolute",bottom:43,right:55,
      fontSize:15,maxWidth:750,textAlign:"right",overflowWrap:"anywhere",
      color:"#d1d8df"}}>Quelle: {scene.source}</div>}
  </AbsoluteFill>;
};

const Doku=({scenes,voiceover,demo})=>{
  let offset=0;
  return <AbsoluteFill style={{background:P.bg}}>
    {scenes.map(s=>{
      const start=offset;
      offset+=s.durationInFrames;
      return <Sequence key={s.sceneId} from={start}
        durationInFrames={s.durationInFrames} name={s.sceneId}>
        <Shot scene={s} demo={demo}/>
      </Sequence>;
    })}
    {voiceover&&<Audio src={staticFile(voiceover)} volume={1}/>}
  </AbsoluteFill>;
};

const Root=()=> <Composition id="DokuVideo" component={Doku}
  defaultProps={example} fps={30} width={1920} height={1080}
  durationInFrames={90} calculateMetadata={({props})=>({
    fps:props.fps,width:props.width,height:props.height,
    durationInFrames:props.durationInFrames})}/>;
registerRoot(Root);
