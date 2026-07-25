// ============================================================
// 3D 生成素材映射（AI 生成的空间封面 / 家具物件图）
// 必须 import 引用才会被 webpack 打包进 dist（字符串路径不拷贝）
// ============================================================

// ---------- 空间模板封面（6 张，对应 mockSpaceTemplates） ----------
import frenchLivingImg from '@/assets/scenes/french-living.jpg'
import minimalBedroomImg from '@/assets/scenes/minimal-bedroom.jpg'
import chineseStudyImg from '@/assets/scenes/chinese-study.jpg'
import kidsRoomImg from '@/assets/scenes/kids-room.jpg'
import petSpaceImg from '@/assets/scenes/pet-space.jpg'
import euroDiningImg from '@/assets/scenes/euro-dining.jpg'

// ---------- 场景改造封面（4 张，对应 mockScenes 四个 MVP 场景；按场景功能单独绘制） ----------
import scenePetImg from '@/assets/scenes/scene-pet.png'
import sceneBabyImg from '@/assets/scenes/scene-baby.png'
import sceneFengshuiImg from '@/assets/scenes/scene-fengshui.png'
import sceneFlowImg from '@/assets/scenes/scene-flow.png'

// ---------- 家具物件图（14 张，对应 mockFurniture 各 SKU） ----------
import sofa01Img from '@/assets/furniture/sofa-01.jpg'
import sofa02Img from '@/assets/furniture/sofa-02.jpg'
import sofa03Img from '@/assets/furniture/sofa-03.jpg'
import bed01Img from '@/assets/furniture/bed-01.jpg'
import bed02Img from '@/assets/furniture/bed-02.jpg'
import bed03Img from '@/assets/furniture/bed-03.jpg'
import table01Img from '@/assets/furniture/table-01.jpg'
import table02Img from '@/assets/furniture/table-02.jpg'
import table03Img from '@/assets/furniture/table-03.jpg'
import chair01Img from '@/assets/furniture/chair-01.jpg'
import chair02Img from '@/assets/furniture/chair-02.jpg'
import chair03Img from '@/assets/furniture/chair-03.jpg'
import cabinet01Img from '@/assets/furniture/cabinet-01.jpg'
import cabinet02Img from '@/assets/furniture/cabinet-02.jpg'
import cabinet03Img from '@/assets/furniture/cabinet-03.jpg'
import lamp01Img from '@/assets/furniture/lamp-01.jpg'
import lamp02Img from '@/assets/furniture/lamp-02.jpg'
import lamp03Img from '@/assets/furniture/lamp-03.jpg'
import babybed01Img from '@/assets/furniture/babybed-01.jpg'
import pet01Img from '@/assets/furniture/pet-01.jpg'

/** 空间模板 id → 封面图 */
export const spaceTemplateImages: Record<string, string> = {
  tpl_french_living: frenchLivingImg,
  tpl_minimal_bedroom: minimalBedroomImg,
  tpl_chinese_study: chineseStudyImg,
  tpl_kids_room: kidsRoomImg,
  tpl_pet_space: petSpaceImg,
  tpl_euro_dining: euroDiningImg,
}

/** 场景 id → 封面图（养宠=猫爬架 / 养娃=圆角家具 / 风水=新中式整屋 45° 布局 / 动线=通透少物） */
export const sceneImages: Record<string, string> = {
  scene_pet: scenePetImg,
  scene_baby: sceneBabyImg,
  scene_fengshui: sceneFengshuiImg,
  scene_flow: sceneFlowImg,
}

/** 家具 SKU id → 物件图 */
export const furnitureImages: Record<string, string> = {
  f_sofa_01: sofa01Img,
  f_sofa_02: sofa02Img,
  f_sofa_03: sofa03Img,
  f_bed_01: bed01Img,
  f_bed_02: bed02Img,
  f_bed_03: bed03Img,
  f_table_01: table01Img,
  f_table_02: table02Img,
  f_table_03: table03Img,
  f_chair_01: chair01Img,
  f_chair_02: chair02Img,
  f_chair_03: chair03Img,
  f_cabinet_01: cabinet01Img,
  f_cabinet_02: cabinet02Img,
  f_cabinet_03: cabinet03Img,
  f_lamp_01: lamp01Img,
  f_lamp_02: lamp02Img,
  f_lamp_03: lamp03Img,
  f_babybed_01: babybed01Img,
  f_pet_01: pet01Img,
}
