<script setup lang="ts">
const asideMenuList = [
  '会话管理',
  '角色配置',
  '模拟器',
  '数据分析',
  'APL 编辑器',
  '角色支持列表',
  'APL 设计书',
  '贡献指南',
]
const activedMenu = ref('会话管理')
</script>

<template>
  <div class="w-100dvw h-100dvh bg-#F1F1F1 overflow-hidden">
    <!-- 侧栏 -->
    <div class="w-192px h-full overflow-hidden absolute top-0 left-0 flex flex-col text-14px">
      <!-- 侧边顶部 -->
      <div class="shrink-0 w-full h-72px p-16px text-28px font-700">
        ZSim
      </div>

      <!-- 侧边列表 -->
      <div class="flex-1 w-full overflow-auto flex flex-col">
        <div
          v-for="menu in asideMenuList"
          :key="menu"
          class="
            shrink-0 h-40px my-1px mx-8px px-10px overflow-hidden
            rounded-8px border border-solid
            flex items-center gap-8px text-#6B6B6B
            select-none cursor-pointer
          "
          :class="[
            menu === activedMenu
              ? 'border-#0000001A bg-white'
              : 'border-transparent hover:bg-#38302E0D active:bg-#38302E17',
          ]"
          @click="activedMenu = menu"
        >
          <div class="w-16px h-16px rounded-sm bg-#6B6B6B40" />
          <div>{{ menu }}</div>
        </div>
      </div>

      <!-- 侧边底部 -->
      <div class="shrink-0 w-full h-64px p-16px pb-24px">
        06 号
      </div>
    </div>

    <!-- 模块 -->
    <div
      class="
        w-[calc(100%-192px-16px)] h-[calc(100%-32px)] m-16px ml-0
        absolute left-192px overflow-hidden
        flex flex-col
        bg-#FFF rounded-8px border border-solid border-#E6E6E6
      "
    >
      <!-- 模块.1 -->
      <div class="w-full shrink-0 p-24px pb-0 text-24px font-400">
        {{ activedMenu }}
      </div>

      <!-- 模块.2 -->
      <div class="w-[calc(100%-48px)] shrink-0 mx-24px h-56px flex items-center justify-between">
        <div>
          info left
        </div>
        <div class="px-10px h-32px rounded-8px bg-#FA7319 flex items-center text-14px text-white cursor-pointer select-none hover:brightness-90 active:brightness-80">
          创建会话
        </div>
      </div>

      <!-- 模块.3 -->
      <div class="w-full flex-1 overflow-auto flex gap-16px">
        <div class="shrink-0 w-248px h-767px ml-24px my-16px bg-#F1F1F1 rounded-12px border border-solid border-#E6E6E6" />
        <div class="shrink-0 w-248px h-522px my-16px bg-#F1F1F1 rounded-12px border border-solid border-#E6E6E6" />
        <div class="shrink-0 w-248px h-277px my-16px bg-#F1F1F1 rounded-12px border border-solid border-#E6E6E6" />
        <div class="shrink-0 w-248px h-522px mr-24px my-16px bg-#F1F1F1 rounded-12px border border-solid border-#E6E6E6" />
      </div>
    </div>
  </div>
</template>
