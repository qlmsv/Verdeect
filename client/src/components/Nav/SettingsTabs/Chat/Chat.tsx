import { memo } from 'react';
import FontSizeSelector from './FontSizeSelector';
import ToggleSwitch from '../ToggleSwitch';
import store from '~/store';

const toggleSwitchConfigs = [
  {
    stateAtom: store.enterToSend,
    localizationKey: 'com_nav_enter_to_send',
    switchId: 'enterToSend',
    hoverCardText: 'com_nav_info_enter_to_send',
    key: 'enterToSend',
  },
  {
    stateAtom: store.maximizeChatSpace,
    localizationKey: 'com_nav_maximize_chat_space',
    switchId: 'maximizeChatSpace',
    hoverCardText: undefined,
    key: 'maximizeChatSpace',
  },
  {
    stateAtom: store.saveDrafts,
    localizationKey: 'com_nav_save_drafts',
    switchId: 'saveDrafts',
    hoverCardText: 'com_nav_info_save_draft',
    key: 'saveDrafts',
  },
];

function Chat() {
  return (
    <div className="flex flex-col gap-3 p-1 text-sm text-text-primary">
      <div className="pb-3">
        <FontSizeSelector />
      </div>
      {toggleSwitchConfigs.map((config) => (
        <div key={config.key} className="pb-3">
          <ToggleSwitch
            stateAtom={config.stateAtom}
            localizationKey={config.localizationKey}
            hoverCardText={config.hoverCardText}
            switchId={config.switchId}
          />
        </div>
      ))}
    </div>
  );
}

export default memo(Chat);
