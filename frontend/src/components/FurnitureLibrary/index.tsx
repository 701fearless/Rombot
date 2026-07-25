import { ScrollView, Text, View } from '@tarojs/components'
import CoverImage from '@/components/CoverImage'
import './index.scss'

export interface FurnitureLibraryProps {
  items: Array<{ id: string; coverUrl: string; title: string }>
  onAdd?: () => void
  onOpen?: () => void
  onSelect?: (id: string) => void
  selectedId?: string
}

export default function FurnitureLibrary({
  items,
  onAdd,
  onOpen,
  onSelect,
  selectedId,
}: FurnitureLibraryProps) {
  return (
    <View className='furniture-library'>
      <View
        className={`furniture-library__head ${onOpen ? 'is-clickable' : ''}`}
        onClick={onOpen}
      >
        <Text className='furniture-library__title'>家具库</Text>
        <Text className='furniture-library__meta'>
          {onOpen ? `查看全部 · ${items.length} 件` : `${items.length} 件可试摆`}
        </Text>
      </View>
      <ScrollView className='furniture-library__rail' scrollX enhanced showScrollbar={false}>
        {onAdd && (
          <View
            className='furniture-library__card furniture-library__card--add'
            onClick={onAdd}
          >
            <View className='furniture-library__add-body'>
              <Text className='furniture-library__add-plus'>＋</Text>
            </View>
            <Text className='furniture-library__name'>截图建模</Text>
          </View>
        )}
        {items.map((item) => (
          <View
            key={item.id}
            className={`furniture-library__card ${selectedId === item.id ? 'is-selected' : ''}`}
            onClick={() => onSelect?.(item.id)}
          >
            <View className='furniture-library__cover'>
              <CoverImage src={item.coverUrl} title={item.title} ratio='1 / 1' />
              {selectedId === item.id && (
                <View className='furniture-library__selected'>
                  <Text className='furniture-library__selected-text'>已加入</Text>
                </View>
              )}
            </View>
            <Text className='furniture-library__name'>{item.title}</Text>
          </View>
        ))}
      </ScrollView>
    </View>
  )
}
