package ai.teammoon.pli.domain

/** Code point offsets never split a Korean character or an emoji surrogate pair. */
class ReadingContext(val text:String,val identity:String,val sourceScope:String,val intentRevision:Long,private val limit:Int=420){
    private val starts=mutableListOf(0)
    var page=0;private set
    val hasMore get()=end(starts[page])<text.length
    private fun end(start:Int):Int{
        val count=text.codePointCount(start,text.length)
        val maximum=text.offsetByCodePoints(start,minOf(count,limit))
        if(maximum==text.length)return maximum
        val boundary=(start+1 until maximum).lastOrNull{text[it] in charArrayOf('.','!','?','\n')}
        return if(boundary!=null&&boundary-start>limit/3)boundary+1 else maximum
    }
    fun current()=text.substring(starts[page],end(starts[page])).trim()
    fun next():Boolean{val next=end(starts[page]);if(next>=text.length)return false;if(page+1==starts.size)starts.add(next);page++;return true}
    fun previous():Boolean{if(page==0)return false;page--;return true}
    fun first(){page=0}
}
