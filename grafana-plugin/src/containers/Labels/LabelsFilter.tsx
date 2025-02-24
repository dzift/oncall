import React, { useEffect, useState } from 'react';

import { SelectableValue } from '@grafana/data';
import cn from 'classnames/bind';
import { observer } from 'mobx-react';

import LabelsFilterComponent from 'components/LabelsFilter/LabelsFilter';
import { useStore } from 'state/useStore';

import styles from './Labels.module.css';

const cx = cn.bind(styles);

interface LabelsFilterProps {
  filterType: 'labels' | 'alert_group_labels';
  autoFocus: boolean;
  className: string;
  value: string[];
  onChange: (value: Array<{ key: SelectableValue<string>; value: SelectableValue<string> }>) => void;
}

const LabelsFilter = observer((props: LabelsFilterProps) => {
  const { filterType, className, autoFocus, value: propsValue, onChange } = props;
  const [value, setValue] = useState([]);
  const [keys, setKeys] = useState([]);
  const { alertGroupStore, labelsStore } = useStore();

  const loadKeys =
    filterType === 'alert_group_labels'
      ? alertGroupStore.loadLabelsKeys.bind(alertGroupStore)
      : labelsStore.loadKeys.bind(labelsStore);

  const loadValuesForKey =
    filterType === 'alert_group_labels'
      ? alertGroupStore.loadValuesForLabelKey.bind(alertGroupStore)
      : labelsStore.loadValuesForKey.bind(labelsStore);

  useEffect(() => {
    loadKeys().then(setKeys);
  }, []);

  useEffect(() => {
    const keyValuePairs = (propsValue || []).map((k) => k.split(':'));
    const promises = keyValuePairs.map(([keyId]) => loadValuesForKey(keyId));
    const fetchKeyValues = async () => await Promise.all(promises);

    fetchKeyValues().then((list) => {
      const value = list.map(({ key, values }, index) => ({
        key,
        value: values.find((v) => v.id === keyValuePairs[index][1]) || {},
      }));

      setValue(value);
    });
  }, [propsValue, keys]);

  const handleLoadOptions = (search) => {
    if (!search) {
      return Promise.resolve([]);
    }

    return new Promise((resolve) => {
      const keysFiltered = keys.filter((k) => k.name.toLowerCase().includes(search.toLowerCase()));

      const promises = keysFiltered.map((key) => loadValuesForKey(key.id));

      Promise.all(promises).then((list) => {
        const options = list.reduce((memo, { key, values }) => {
          const options = values.map((value) => ({ key, value }));

          return [...memo, ...options];
        }, []);

        resolve(options);
      });
    });
  };

  return (
    <div className={cx('root', className)}>
      <LabelsFilterComponent
        autoFocus={autoFocus}
        labelField="name"
        value={value}
        onChange={onChange}
        onLoadOptions={handleLoadOptions}
      />
    </div>
  );
});

export default LabelsFilter;
