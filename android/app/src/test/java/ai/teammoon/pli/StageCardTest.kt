package ai.teammoon.pli

import ai.teammoon.pli.domain.*
import org.junit.Assert.*
import org.junit.Test

class StageCardTest{
    private val pack=StageCards.build("pack","내일 챙길 것","숲 체험 · 내일 비가 온대",listOf(CardSection("",listOf(
        CardItem("👟","운동화","숲 체험 공지"),CardItem("💧","물병","숲 체험 공지"),CardItem("☂️","우산","내일 비 9mm"),CardItem("🥾","장화","내일 비 9mm")))))!!
    @Test fun packCardKeepsItsItems(){assertEquals(listOf("운동화","물병","우산","장화"),pack.items.map{it.label});assertFalse(pack.complete)}
    @Test fun spokenPackingTicksItems(){
        assertEquals(setOf("물병"),StageCards.ticked(pack,"물병 챙겼어"));assertEquals(setOf("물병"),StageCards.ticked(pack,"물병 챙겨어"));assertTrue("a request is not a tick",StageCards.ticked(pack,"물병 챙겨").isEmpty())
        assertEquals(setOf("우산","장화"),StageCards.ticked(pack,"우산이랑 장화 넣었어"))
        assertEquals(pack.items.map{it.label}.toSet(),StageCards.ticked(pack,"다 챙겼어!"))
        assertTrue("not packing talk",StageCards.ticked(pack,"물병은 어디 있어?").isEmpty())
        assertTrue(pack.copy(checked=pack.items.map{it.label}.toSet()).complete)}
    @Test fun routeCardsAreNotTickedAndEmptyCardsAreDropped(){
        val route=StageCards.build("route","숲 체험 가는 길","도착까지 12분",listOf(CardSection("가는 길 놀이",listOf(CardItem("🌳","숲 퀴즈 5문제","도착까지 12분")))),"NATURE")!!
        assertTrue(StageCards.ticked(route,"다 챙겼어").isEmpty());assertEquals("NATURE",route.game)
        assertNull(StageCards.build("pack","","",listOf(CardSection("",listOf(CardItem("","","")))))) }
    @Test fun startingTheSuggestedGameNeedsAYes(){for(s in listOf("응","좋아!","시작","하자"))assertTrue(s,StageCards.accepts(s));for(s in listOf("싫어","고래는 물고기야"))assertFalse(s,StageCards.accepts(s))}
}
