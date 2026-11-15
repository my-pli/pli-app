package ai.teammoon.pli.voice
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
object PcmWav{
 fun read(file:File):ByteArray{
  require(file.length() in 44..32*1024*1024){"음성 파일 크기가 올바르지 않습니다"}
  val bytes=file.readBytes();require(String(bytes,0,4)=="RIFF"&&String(bytes,8,4)=="WAVE"){"WAV 파일이 필요합니다"}
  val buffer=ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN);var offset=12;var formatOkay=false
  while(offset+8<=bytes.size){val name=String(bytes,offset,4);val length=buffer.getInt(offset+4);require(length>=0&&offset+8L+length<=bytes.size){"손상된 WAV 파일"}
   if(name=="fmt "){require(length>=16);formatOkay=buffer.getShort(offset+8).toInt()==1&&buffer.getShort(offset+10).toInt()==1&&buffer.getInt(offset+12)==16000&&buffer.getShort(offset+22).toInt()==16}
   if(name=="data"){require(formatOkay){"16kHz mono 16-bit PCM WAV가 필요합니다"};return bytes.copyOfRange(offset+8,offset+8+length)}
   offset+=8+length+(length%2)
  };error("WAV 음성 데이터가 없습니다")
 }
}
