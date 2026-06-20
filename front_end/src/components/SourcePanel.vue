<template>
  <div class="source-panel" :class="variant">
    <div :class="['source-total', !expanded ? 'source-total-last' : '']">
      <span v-if="language === 'zh'"> 找到了{{ viewModel.totalCount }}个信息来源： </span>
      <span v-else> Found {{ viewModel.totalCount }} source of information </span>
      <span v-if="viewModel.webSearchTriggered" class="web-badge">
        <SvgIcon name="network" :size="12" />
        联网搜索
      </span>
      <SvgIcon v-show="!expanded" name="down" @click="expanded = !expanded" />
      <SvgIcon v-show="expanded" name="up" @click="expanded = !expanded" />
    </div>
    <Transition name="sourceitem">
      <div v-show="expanded" class="source-list">
        <div v-for="group in viewModel.groups" :key="group.type" class="source-group">
          <div class="group-header">
            <span class="group-label">{{ group.label }}</span>
            <span class="group-count">{{ group.count }}个</span>
          </div>
          <div
            v-for="(sourceItem, sourceIndex) in group.items"
            :key="sourceItem.id"
            class="data-source"
          >
            <p v-show="sourceItem.name" class="control">
              <span class="tips">{{ common.dataSource }}{{ sourceIndex + 1 }}:</span>
              <a
                v-if="sourceItem.isExternalLink"
                :href="sourceItem.linkUrl || undefined"
                target="_blank"
              >
                {{ sourceItem.name }}
              </a>
              <span
                v-else
                :class="['file', sourceItem.isPreviewable ? 'filename-active' : '']"
                @click="handleItemClick(sourceItem)"
              >
                {{ sourceItem.name }}
              </span>
              <span :class="['score-badge', `score-${sourceItem.scoreLevel}`]">
                {{ sourceItem.scoreText }}
              </span>
              <SvgIcon
                v-show="isDetailOpen(sourceItem.id)"
                name="iconup"
                @click="toggleDetail(sourceItem.id)"
              />
              <SvgIcon
                v-show="!isDetailOpen(sourceItem.id)"
                name="icondown"
                @click="toggleDetail(sourceItem.id)"
              />
            </p>
            <Transition name="sourceitem">
              <div v-show="isDetailOpen(sourceItem.id)" class="source-content">
                <HighLightMarkDown
                  v-if="contentMode === 'markdown'"
                  :content="sourceItem.content || ''"
                />
                <p v-else v-html="(sourceItem.content || '').replaceAll('\n', '<br/>')"></p>
                <p class="score">
                  <span class="tips">{{ common.correlation }}</span>
                  {{ sourceItem.scoreText }}
                </p>
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue';
import { storeToRefs } from 'pinia';
import { SourcePanelViewModel } from '@/composables/useSourcePresenter';
import { useLanguage } from '@/store/useLanguage';
import { getLanguage } from '@/language';
import { useChatSourceFile } from '@/composables/useChatSourceFile';
import SvgIcon from './SvgIcon.vue';
import HighLightMarkDown from './HighLightMarkDown.vue';

withDefaults(
  defineProps<{
    viewModel: SourcePanelViewModel;
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
const { handleChatSource } = useChatSourceFile();

const expanded = ref(false);
const detailIds = ref<string[]>([]);

const isDetailOpen = (id: string): boolean => {
  return detailIds.value.includes(id);
};

const toggleDetail = (id: string) => {
  if (isDetailOpen(id)) {
    detailIds.value = detailIds.value.filter(i => i !== id);
  } else {
    detailIds.value.push(id);
  }
};

const handleItemClick = (item: SourcePanelViewModel['groups'][0]['items'][0]) => {
  if (!item.isPreviewable) return;
  if ('file_id' in item.raw || 'file_url' in item.raw) {
    handleChatSource(item.raw as any);
  }
};
</script>

<style lang="scss" scoped>
.source-panel {
  .source-total {
    display: flex;
    align-items: center;
    gap: 8px;

    span {
      margin-right: 5px;
    }

    svg {
      width: 16px !important;
      height: 16px !important;
      cursor: pointer !important;
    }

    .web-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 8px;
      background: rgba(90, 71, 229, 0.1);
      color: #5a47e5;
      font-size: 12px;
      border-radius: 10px;
      margin-left: 8px;
    }
  }

  .source-total-last {
    border-radius: 0px 0 12px 12px;
  }

  .source-list {
    border-radius: 0px 12px 12px 12px;
  }

  .source-group {
    & + & {
      border-top: 1px solid $borderColor;
      margin-top: 8px;
      padding-top: 8px;
    }

    .group-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 20px 0;

      .group-label {
        font-size: 13px;
        color: $title2;
        font-weight: 500;
      }

      .group-count {
        font-size: 12px;
        color: $label2;
      }
    }
  }

  .data-source {
    font-size: 14px;
    line-height: 22px;
    color: $title1;

    .control {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 4px;
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
      color: #5a47e5;
      text-decoration: underline;
    }

    .score-badge {
      display: inline-block;
      padding: 0 6px;
      font-size: 12px;
      border-radius: 4px;
      margin-right: 8px;
      min-width: 36px;
      text-align: center;

      &.score-high {
        background: rgba(82, 196, 26, 0.1);
        color: #52c41a;
      }

      &.score-medium {
        background: rgba(250, 173, 20, 0.1);
        color: #faad14;
      }

      &.score-low {
        background: rgba(255, 77, 79, 0.1);
        color: #ff4d4f;
      }

      &.score-unknown {
        background: rgba(0, 0, 0, 0.06);
        color: $label2;
      }
    }

    a {
      color: #5a47e5;
      text-decoration: underline;
      cursor: pointer;
      margin-right: 8px;
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

        .file {
          max-width: 100%;
          word-wrap: break-word;
          overflow-wrap: break-word;
        }
      }

      &:last-child {
        border-radius: 0px 0px 12px 12px;
      }

      &:first-child {
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
