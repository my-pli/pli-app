package ai.teammoon.pli.ui

import android.provider.Settings
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.Density
import ai.teammoon.pli.R
import ai.teammoon.pli.domain.*
import kotlinx.coroutines.delay

private val Bg=Color.Transparent // the night backdrop shows through (StageBackdrop)
private val Card=Color(0x22FFFFFF)
private val Cream=Stage.Cream
private val Gold=Stage.Gold
private val Sage=Stage.Soft
private val Face=FontFamily(Font(R.font.pretendard))

@Composable private fun ExperienceTheme(content:@Composable ()->Unit){
    BoxWithConstraints(Modifier.fillMaxSize()){
        val base=LocalDensity.current
        val scale=minOf(maxWidth.value/900f,maxHeight.value/600f).coerceIn(1f,1.8f)
        CompositionLocalProvider(LocalDensity provides Density(base.density*scale,base.fontScale)){
            MaterialTheme{content()}
        }
    }
}

@Composable private fun reducedMotion():Boolean{val context=LocalContext.current;return remember{Settings.Global.getFloat(context.contentResolver,Settings.Global.ANIMATOR_DURATION_SCALE,1f)==0f}}
@Composable private fun Heading(label:String,title:String){
    Text("pli · $label",fontFamily=Face,fontSize=18.sp,color=Gold)
    Spacer(Modifier.height(20.dp));Text(title,fontFamily=Face,fontSize=34.sp,fontWeight=FontWeight.Medium,color=Cream,maxLines=2,overflow=TextOverflow.Ellipsis)
}
@Composable private fun ListeningFooter(state:ConversationState){
    Spacer(Modifier.height(18.dp))
    Text(when{state.sessionStatus=="STOPPED"->"마이크를 껐어요. 시작 버튼으로 다시 연결해 주세요.";state.quiet->"조용히 기다려요. “다시 시작해”라고 말해 주세요.";state.playback=="PLAYING"->"플리의 말을 들어보세요.";state.recognition!="READY"->"다음 질문을 준비하고 있어요.";else->"다음은 목소리로. “숫자 놀이 해줘” · “오늘 준비물 알려줘”"},fontFamily=Face,fontSize=15.sp,color=Sage,maxLines=2)
}

@Composable fun GrowthOverview(state:ConversationState){
    val g=remember(state.memories){GrowthSummary.from(state.memories)}
    ExperienceTheme{Surface(Modifier.fillMaxSize(),color=Bg){
        Column(Modifier.fillMaxSize().padding(28.dp)){
            Heading("우리 가족의 기록","함께한 시간이, 차곡차곡.")
            Text(if(state.demo)"공개 체험에서 만든 기록 · 개인 기록은 표시하지 않아요."else"이 기기에 저장한 여정에서만 계산했어요.",fontFamily=Face,fontSize=14.sp,color=Sage,modifier=Modifier.padding(top=10.dp,bottom=22.dp))
            if(state.vehicle.uxRestricted){Text(state.speech,fontFamily=Face,fontSize=25.sp,lineHeight=39.sp,color=Cream,maxLines=3,overflow=TextOverflow.Ellipsis);Spacer(Modifier.weight(1f))}
            else{Column(Modifier.weight(1f).verticalScroll(rememberScrollState())){
                Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(14.dp)){
                    Metric("도착 스탬프","${g.stamps}개",Modifier.weight(1f))
                    Metric("함께 달린 거리",g.kilometers?.let{"%.1f km".format(it)}?:"미수신",Modifier.weight(1f))
                    Metric("저장된 문제 정답률",g.accuracy?.let{"$it%"}?:"기록 전",Modifier.weight(1f))
                }
                Spacer(Modifier.height(20.dp))
                Surface(shape=RoundedCornerShape(20.dp),color=Card){Column(Modifier.fillMaxWidth().padding(20.dp)){
                    Text("최근 7일의 도착",fontFamily=Face,fontSize=17.sp,color=Cream)
                    Row(Modifier.fillMaxWidth().height(100.dp),horizontalArrangement=Arrangement.spacedBy(10.dp),verticalAlignment=Alignment.Bottom){
                        g.dailyStamps.forEachIndexed{i,n->Column(Modifier.weight(1f),horizontalAlignment=Alignment.CenterHorizontally){Text("$n",color=Sage,fontSize=12.sp);Spacer(Modifier.height(5.dp));Box(Modifier.fillMaxWidth().height(if(n==0)1.dp else(16+52f*n/(g.dailyStamps.maxOrNull()?:1).coerceAtLeast(1)).dp).clip(RoundedCornerShape(5.dp)).background(if(n>0)Gold else Stage.GlassEdge));Text(if(i==6)"오늘"else"${6-i}일 전",color=Sage,fontFamily=Face,fontSize=11.sp,modifier=Modifier.padding(top=7.dp))}}
                }}}
                Spacer(Modifier.height(18.dp))
                if(g.recent.isEmpty())Text("첫 번째 여정이 기다리고 있어요.\n함께 출발하고 “도착했어”라고 말해 주세요.",fontFamily=Face,fontSize=18.sp,color=Sage,lineHeight=28.sp)
                else g.recent.forEach{m->Row(Modifier.fillMaxWidth().padding(vertical=7.dp),horizontalArrangement=Arrangement.SpaceBetween){Text("${m.date} · ${m.destination}",fontFamily=Face,fontSize=15.sp,color=Cream,modifier=Modifier.weight(1f),maxLines=1,overflow=TextOverflow.Ellipsis);Text("${m.correct}/${m.answered} 성공",fontFamily=Face,fontSize=14.sp,color=Gold)}}
            }}
            ListeningFooter(state)
        }
    }}
}
@Composable private fun Metric(label:String,value:String,modifier:Modifier){Surface(modifier,shape=RoundedCornerShape(18.dp),color=Card){Column(Modifier.padding(18.dp)){Text(label,fontFamily=Face,fontSize=12.sp,color=Sage);Spacer(Modifier.height(13.dp));Text(value,fontFamily=Face,fontSize=26.sp,fontWeight=FontWeight.Medium,color=Gold,maxLines=1)}}}

@Composable fun AbacusPanel(state:ConversationState,modifier:Modifier=Modifier){
    val values=remember(state.question){AbacusSteps.values(state.question)}
    val reduce=reducedMotion();var stage by remember(state.question){mutableIntStateOf(0)}
    LaunchedEffect(state.question,state.abacusHint,state.quiet,reduce){stage=0;if(state.abacusHint&&!state.quiet){if(reduce)stage=(values.size-1).coerceAtLeast(0)else for(i in values.indices){stage=i;delay(1400)}}}
    val value=values.getOrNull(stage)?:0
    val digits=listOf(value/10,value%10)
    val positions=digits.flatMap{digit->(0..4).map{bead->val active=if(bead==0)digit>=5 else bead<=digit%5;val y=if(bead==0){if(active).22f else .09f}else if(active).36f+(bead-1)*.105f else .64f+(bead-1)*.08f;animateFloatAsState(y,tween(if(reduce)0 else 320),label="abacus-bead").value to active}}
    Column(modifier,horizontalAlignment=Alignment.CenterHorizontally){
        Text(if(state.abacusHint)"한 알씩, 함께 생각해요."else"머릿속에 작은 주판을 놓아요.",fontFamily=Face,fontSize=21.sp,color=Gold)
        Canvas(Modifier.fillMaxWidth().weight(1f).semantics{contentDescription="두 자리 주판, 표시 값 $value"}){
            val left=size.width*.18f;val right=size.width*.82f;val top=size.height*.04f;val bottom=size.height*.96f
            drawRoundRect(Card,Offset(left-18.dp.toPx(),top),Size(right-left+36.dp.toPx(),bottom-top),androidx.compose.ui.geometry.CornerRadius(18.dp.toPx()))
            val barY=size.height*.29f;drawLine(Sage.copy(alpha=.7f),Offset(left,barY),Offset(right,barY),3.dp.toPx())
            digits.forEachIndexed{col,_->val x=size.width*(if(col==0).36f else .64f);drawLine(Sage.copy(alpha=.35f),Offset(x,top+12),Offset(x,bottom-12),2.dp.toPx());for(bead in 0..4){val p=positions[col*5+bead];val beadWidth=(right-left)*.23f;val beadHeight=size.height*.067f;drawRoundRect(if(p.second)Gold else Stage.Aurora,Offset(x-beadWidth/2,size.height*p.first-beadHeight/2),Size(beadWidth,beadHeight),androidx.compose.ui.geometry.CornerRadius(beadHeight/2));drawLine(Color.White.copy(alpha=.2f),Offset(x-beadWidth*.27f,size.height*p.first-beadHeight*.2f),Offset(x+beadWidth*.27f,size.height*p.first-beadHeight*.2f),2f)}}
        }
        Text(if(state.abacusHint)values.joinToString("  →  ")else"힌트가 필요하면 “힌트 줘”",fontFamily=Face,fontSize=22.sp,color=Cream,modifier=Modifier.padding(top=8.dp))
    }
}

@Composable fun ChargingPlayground(state:ConversationState){
    ExperienceTheme{Surface(Modifier.fillMaxSize(),color=Bg){Column(Modifier.fillMaxSize().padding(28.dp)){
        Heading("충전 놀이터",if(state.vehicle.uxRestricted)"주행 중에는 목소리로."else"차가 쉬는 동안, 한 문제 더.")
        Row(Modifier.fillMaxWidth().padding(vertical=20.dp),horizontalArrangement=Arrangement.SpaceBetween){Text(state.vehicle.battery?.let{"배터리 $it%"}?:"배터리 신호 확인 전",fontFamily=Face,fontSize=22.sp,color=Gold);Text(when(state.vehicle.chargingActive){true->"차량 충전 활성화";false->"차량 충전 비활성화";else->"충전 활성 신호 미수신"},fontFamily=Face,fontSize=14.sp,color=Sage)}
        state.vehicle.battery?.let{battery->LinearProgressIndicator(progress=battery/100f,modifier=Modifier.fillMaxWidth().height(6.dp),color=Gold,trackColor=Card)}
        Spacer(Modifier.height(18.dp));Text(state.title,fontFamily=Face,fontSize=28.sp,color=Cream,maxLines=2)
        if(!state.vehicle.uxRestricted)AbacusPanel(state,Modifier.weight(1f).fillMaxWidth().padding(vertical=12.dp))else{Spacer(Modifier.weight(1f));Text(state.speech,fontFamily=Face,fontSize=24.sp,color=Cream,maxLines=3,overflow=TextOverflow.Ellipsis);Spacer(Modifier.weight(1f))}
        ListeningFooter(state)
    }}}
}

@Composable fun DestinationOptions(state:ConversationState){
    ExperienceTheme{Surface(Modifier.fillMaxSize(),color=Bg){Column(Modifier.fillMaxSize().padding(28.dp)){
        Heading("가족의 다음 목적지 · ${state.destinationPage+1}/${((state.destinationChoices.size+2)/3).coerceAtLeast(1)}",state.title)
        Text(state.answerSource,fontFamily=Face,fontSize=14.sp,color=Sage,modifier=Modifier.padding(vertical=18.dp))
        if(state.vehicle.uxRestricted)Text(state.speech,fontFamily=Face,fontSize=24.sp,lineHeight=36.sp,color=Cream,maxLines=3,overflow=TextOverflow.Ellipsis)
        else if(state.destinationChoices.isEmpty())Text("이 컴퓨터의 가족 연결 화면에서\n보호자가 후보를 등록해 주세요.",fontFamily=Face,fontSize=22.sp,color=Sage,lineHeight=34.sp)
        else state.destinationChoices.drop(state.destinationPage*3).take(3).forEachIndexed{i,c->Surface(Modifier.fillMaxWidth().padding(bottom=12.dp),shape=RoundedCornerShape(18.dp),color=if(c==state.selectedDestination)Stage.Violet.copy(alpha=.35f)else Card){Row(Modifier.padding(22.dp),verticalAlignment=Alignment.CenterVertically){Text("${state.destinationPage*3+i+1}",fontSize=22.sp,color=Gold);Text(c.name,fontFamily=Face,fontSize=22.sp,color=Cream,modifier=Modifier.padding(start=20.dp),maxLines=1,overflow=TextOverflow.Ellipsis)}}}
        Spacer(Modifier.weight(1f));Text(when{state.selectedDestination==null->"“첫 번째로 갈래”처럼 말해 주세요.";state.title=="보호자 확인을 기다려요."->"보호자와 함께 장소를 확인한 뒤\n“보호자 확인”이라고 말해 주세요.";else->state.speech},fontFamily=Face,fontSize=18.sp,color=Gold,maxLines=3,overflow=TextOverflow.Ellipsis)
        ListeningFooter(state)
    }}}
}
