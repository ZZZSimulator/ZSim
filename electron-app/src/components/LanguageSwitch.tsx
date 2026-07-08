import { FC } from 'react';
import { useLanguage } from '../hooks/useLanguage';

interface LanguageSwitchProps {
  className?: string;
}

export const LanguageSwitch: FC<LanguageSwitchProps> = ({ className = '' }) => {
  const { language, setLanguage } = useLanguage();

  return (
    <div className={`flex gap-[4px] ${className}`}>
      <button
        type="button"
        data-language-option="zh"
        aria-pressed={language === 'zh'}
        className={`
          px-[10px] h-[32px] rounded-[8px] flex items-center text-[14px] text-white cursor-pointer select-none hover:brightness-90 active:brightness-80
          ${language === 'zh' ? 'bg-[#FA7319]' : 'bg-[#333]'}
        `}
        onClick={() => setLanguage('zh')}
      >
        中文
      </button>
      <button
        type="button"
        data-language-option="en"
        aria-pressed={language === 'en'}
        className={`
          px-[10px] h-[32px] rounded-[8px] flex items-center text-[14px] text-white cursor-pointer select-none hover:brightness-90 active:brightness-80
          ${language === 'en' ? 'bg-[#FA7319]' : 'bg-[#333]'}
        `}
        onClick={() => setLanguage('en')}
      >
        English
      </button>
    </div>
  );
};

export default LanguageSwitch;
