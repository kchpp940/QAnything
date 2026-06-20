<template>
  <div class="source-panel" :class="variant">
    <div :class="['source-total', !expanded ? 'source-total-last' : '']">
      <span v-if="language === 'zh'"> 找到了{{ sources.length }}个信息来源： </span>
      <span v-else> Found {{ sources.length }} source of information </span>
      <SvgIcon v-show="!expanded" name="down" @click="expanded = !expanded" />
      <SvgIcon v-show="expanded" name="up" @click="expanded = !expanded" />
    </div>
    <Transition name="sourceitem">
      <div v-show="expanded" class="source-list">
        <div
          v-for="(sourceItem, sourceIndex) in normalizedSources"
          :key="sourceIndex"
          class="data-source"
        >
          <p v-show="sourceItem.file_name" class="control">
            <span class="tips">{{ common.dataSource }}{{ sourceIndex + 1 }}:</span>
            <a v-if="sourceItem.isExternalLink" :href="sourceItem.linkUrl" target="_blank">
              {{ sourceItem.file_name }}
            </a>
            <span
              v-else
              :class="['file', sourceItem.isPreviewable ? 'filename-active' : '']"
              @click="handleSourceClick(sourceItem)"
            >
              {{ sourceItem.file_name }}
            </span>
            <SvgIcon
              v-show="isDetailOpen(sourceIndex)"
              name="iconup"
              @click="toggleDetail(sourceIndex)"
            />
            <SvgIcon
              v-show="!isDetailOpen(sourceIndex)"
              name="icondown"
              @click="toggleDetail(sourceIndex)"
            />
          </p>
          <Transition name="sourceitem">
            <div v-show="isDetailOpen(sourceIndex)" class="source-content">
              <HighLightMarkDown v-if="contentMode === 'markdown'" :content="sourceItem.content" />
              <p v-else v-html="sourceItem.content?.replaceAll('\n', '<br/>')"></p>
              <p class="score">
                <span class="tips">{{ common.correlation }}</span>
                {{ sourceItem.score }}
              </p>
            </div>
          </Transition>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue';
import { IDataSourceItem } from '@/utils/types';
import { useSourcePresenter } from '@/composables/useSourcePresenter';
import SvgIcon from './SvgIcon.vue';
import HighLightMarkDown from './HighLightMarkDown.vue';
import { getLanguage } from '@/language';
import { useLanguage } from '@/store/useLanguage';
import { storeToRefs } from 'pinia';

const props = withDefaults(
  defineProps<{
    sources: IDataSourceItem[];
    variant?: 'home' | 'bots';
    contentMode?: 'markdown' | 'html';
  }>(),
  {
    variant: 'home',
    contentMode: 'markdown',
  }
);

const common = getLanguage().common;
const { language } = storeToRefs(useLanguage());

const { normalizeSources, handleSourceClick } = useSourcePresenter();

const expanded = ref(false);
const detailIdxs = ref<number[]>([]);

const normalizedSources = computed(() => normalizeSources(props.sources));

const isDetailOpen = (sourceIndex: number): boolean => {
  return detailIdxs.value.includes(sourceIndex);
};

const toggleDetail = (sourceIndex: number) => {
  if (isDetailOpen(sourceIndex)) {
    detailIdxs.value = detailIdxs.value.filter(i => i !== sourceIndex);
  } else {
    detailIdxs.value.push(sourceIndex);
  }
};
</script>

<style lang="scss" scoped>
.source-panel {
  .source-total {
    display: flex;
    align-items: center;

    span {
      margin-right: 5px;
    }

    svg {
      width: 16px !important;
      height: 16px !important;
      cursor: pointer !important;
    }
  }

  .source-total-last {
    border-radius: 0px 0 12px 12px;
  }

  .source-list {
    border-radius: 0px 12px 12px 12px;
  }

  .data-source {
    font-size: 14px;
    line-height: 22px;
    color: $title1;

    .control {
      display: flex;
      align-items: center;
    }

    .score {
      margin-top: 26px;
    }

    .source-content {
      margin-top: 26px;
    }

    .tips {
      min-width: 78px;
      height: 22px;
      line-height: 22px;
      color: $title2;
      margin-right: 8px;
    }

    .file {
      color: $baseColor;
      margin-right: 8px;
    }

    .filename-active {
      cursor: pointer;
    }
  }

  &.home {
    .source-total {
      padding: 10px 20px;
      background: #fff;
    }

    .source-list {
      background: #fff;
    }

    .data-source {
      padding: 13px 20px;
    }
  }

  &.bots {
    .source-total {
      padding: 13px 20px;
      margin-left: 48px;
      background: #f9f9fc;
    }

    .source-list {
      margin-left: 48px;
      background: #f9f9fc;
    }

    .data-source {
      padding: 13px 20px;

      .control {
        width: 100%;
        overflow-wrap: break-word;
        flex-wrap: wrap;

        .file {
          max-width: 100%;
          word-wrap: break-word;
          overflow-wrap: break-word;
        }
      }

      &:nth-last-of-type(2) {
        border-radius: 0px 0px 12px 12px;
      }

      &:nth-first-of-type(1) {
        border-radius: 0px 12px 12px 12px;
      }
    }
  }
}

.sourceitem-leave,
.sourceitem-enter-to {
  opacity: 1;
}

.sourceitem-leave-active,
.sourceitem-enter-active {
  transition: all 0.5s ease;
}

.sourceitem-leave-to,
.sourceitem-enter {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
