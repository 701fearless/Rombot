// CoverShelf：平铺横滑封面架（2026-07-25 改版：去 3D 透视/抽取动效，全部平铺，左右滑动选取）
// 每行可带自己的分类 pill（如空间行的 模板空间/扫描所得/平面图所得）
// variant='add' 的封面渲染为「+」新建卡；所有封面点按直接触发业务
import { ScrollView, Text, View } from '@tarojs/components'
import CoverImage from '@/components/CoverImage'
import './index.scss'

export interface ShelfItem {
  id: string
  title: string
  coverUrl?: string
  tag?: string
  tone?: string
  /** 'add' = 「+」新建卡（渲染加号，无封面图） */
  variant?: 'add'
}

export interface ShelfRowData {
  id: string // 'spaces' | 'assets'
  title: string // 如「空间资产库」「家具资产库」
  items: ShelfItem[]
  /** 本行自己的分类 pill（可选） */
  filters?: string[]
  activeFilter?: string
  onFilterChange?: (filter: string) => void
  /** 行内容为空/只有 + 卡时的引导语（可选） */
  emptyHint?: string
}

export interface CoverShelfProps {
  rows: ShelfRowData[]
  onItemClick?: (rowId: string, item: ShelfItem) => void
}

export default function CoverShelf({ rows, onItemClick }: CoverShelfProps) {
  return (
    <View className='cover-shelf'>
      {rows.map((row) => (
        <View key={row.id} className='cover-shelf__row'>
          <View className='cover-shelf__row-header'>
            <Text className='cover-shelf__row-title'>{row.title}</Text>
          </View>

          {/* 本行自己的分类 pill（空间行=来源分类；家具行=品类） */}
          {row.filters && row.filters.length > 0 && (
            <ScrollView scrollX className='cover-shelf__filters' enhanced showScrollbar={false}>
              {row.filters.map((f) => (
                <View
                  key={f}
                  className={`cover-shelf__pill ${row.activeFilter === f ? 'is-active' : ''}`}
                  onClick={() => row.onFilterChange?.(f)}
                >
                  <Text
                    className={`cover-shelf__pill-text ${row.activeFilter === f ? 'is-active' : ''}`}
                  >
                    {f}
                  </Text>
                </View>
              ))}
            </ScrollView>
          )}

          {row.items.length === 0 ? (
            // 空行兜底：浮雕占位，不塌不白屏
            <View className='cover-shelf__empty emboss-inset'>
              <Text className='cover-shelf__empty-text'>
                {row.emptyHint ?? '暂无内容，去识别第一件家具吧'}
              </Text>
            </View>
          ) : (
            <ScrollView scrollX className='cover-shelf__viewport' enhanced showScrollbar={false}>
              <View className='cover-shelf__rail'>
                {row.items.map((item) =>
                  item.variant === 'add' ? (
                    // 「+」新建卡：凹陷虚线示「空位」
                    <View
                      key={item.id}
                      className='cover-shelf__cover cover-shelf__cover--add'
                      onClick={() => onItemClick?.(row.id, item)}
                    >
                      <View className='cover-shelf__add-body'>
                        <Text className='cover-shelf__add-plus'>+</Text>
                      </View>
                      <Text className='cover-shelf__name'>{item.title}</Text>
                    </View>
                  ) : (
                    <View
                      key={item.id}
                      className='cover-shelf__cover'
                      onClick={() => onItemClick?.(row.id, item)}
                    >
                      <CoverImage
                        src={item.coverUrl}
                        title={item.title}
                        ratio='2 / 3'
                        placeholderColor={item.tone}
                      />
                      {item.tag && (
                        <View className='cover-shelf__tag'>
                          <Text className='cover-shelf__tag-text'>{item.tag}</Text>
                        </View>
                      )}
                      <Text className='cover-shelf__name'>{item.title}</Text>
                    </View>
                  ),
                )}
              </View>
            </ScrollView>
          )}

          {/* 只有 + 卡时的行内引导语 */}
          {row.items.length > 0 &&
            row.items.every((it) => it.variant === 'add') &&
            row.emptyHint && <Text className='cover-shelf__hint'>{row.emptyHint}</Text>}
        </View>
      ))}
    </View>
  )
}
