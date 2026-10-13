'use strict';
/* SPDX-License-Identifier: Apache-2.0 */
/*
 * HinLink 5G 模组 —— 状态 / 手动软复位 / 开机行为配置
 *
 * 机理
 * ----
 * 5G 的「复位 / 使能」脚在 DTS 里归 rfkill-gpio，
 * /sys/class/rfkill/rfkillN/state 是 DEVICE_ATTR_RW（可写）：
 *     echo 0  -> 拉复位        echo 1  -> 释放
 * 所以「0 -> 等一会儿 -> 1」就是一次硬复位脉冲。
 *
 * 后端 = /usr/libexec/hinlink-modem，由 rpcd 插件 `hinlink-modem`
 * （/usr/libexec/rpcd/hinlink-modem）转发成 ubus 方法：
 *     status / reset / power_off / power_on / usb_reset
 *
 * 详见 docs/HARDWARE.md §四。
 */

'require view';
'require form';
'require poll';
'require rpc';
'require ui';
'require uci';

var callStatus = rpc.declare({
	object: 'hinlink-modem',
	method: 'status',
	expect: {}
});

var callReset    = rpc.declare({ object: 'hinlink-modem', method: 'reset',     expect: {} });
var callPowerOff = rpc.declare({ object: 'hinlink-modem', method: 'power_off', expect: {} });
var callPowerOn  = rpc.declare({ object: 'hinlink-modem', method: 'power_on',  expect: {} });
var callUsbReset = rpc.declare({ object: 'hinlink-modem', method: 'usb_reset', expect: {} });

/* 轮询时就地更新的节点 */
var nodes = {};

function num(v, unit) {
	return (v === 0 || v) ? (String(v) + (unit || '')) : '—';
}

function applyState(st) {
	st = st || {};

	if (nodes.rfkill) {
		if (st.rfkill_found) {
			var working = (String(st.state) === '1');
			nodes.rfkill.textContent = (st.rfkill_name || st.rfkill_dev || 'wwan') +
				'  ·  ' + (working ? '工作（state=1）' : '复位中（state=0）');
			nodes.rfkill.className = working ? 'label success' : 'label warning';
		}
		else {
			nodes.rfkill.textContent = '未找到 type=wwan 的 rfkill 设备（该机型 DTS 未定义 rfkill-gpio？）';
			nodes.rfkill.className = 'label danger';
		}
	}

	if (nodes.reg)
		nodes.reg.textContent = st.regulator ? st.regulator
			: '（该机型无独立供电级 —— H69K 只有一路，属正常）';

	if (nodes.usb)
		nodes.usb.textContent = st.usb_dev
			? (st.usb_dev + '   ' + (st.usb_vid || '') + ':' + (st.usb_pid || ''))
			: '未匹配到常见模组 USB（VID 白名单）';

	if (nodes.tty)
		nodes.tty.textContent = st.usb_tty ? st.usb_tty
			: '无 /dev/ttyUSB* · /dev/cdc-wdm* · /dev/ttyACM*';

	if (nodes.timing)
		nodes.timing.textContent = '拉复位 ' + num(st.hold_ms) + ' ms，释放后等 ' + num(st.boot_wait) + ' s';
}

function row(label, key) {
	nodes[key] = E('em', {}, '—');
	return E('tr', { 'class': 'tr' }, [
		E('td', { 'class': 'td left', 'width': '22%' }, label),
		E('td', { 'class': 'td left' }, [ nodes[key] ])
	]);
}

function actionButton(label, fn, kind) {
	return E('button', {
		'class': 'btn cbi-button ' + (kind || 'cbi-button-action'),
		'click': function(ev) {
			ev.preventDefault();

			ui.showModal(label, [
				E('p', { 'class': 'spinner' }, '执行中，请勿关闭页面…')
			]);

			return fn()
				.then(function() { return ui.hideModal(); })
				.then(function() { return callStatus(); })
				.then(function(st) {
					applyState(st);
					ui.addNotification(null, E('p', {}, label + '：已下发'), 'info');
				})
				.catch(function(e) {
					ui.hideModal();
					ui.addNotification(null, E('p', {}, String((e && e.message) || e)), 'error');
				});
		}
	}, label);
}

return view.extend({
	load: function() {
		return Promise.all([
			callStatus(),
			uci.load('hinlink-modem')
		]);
	},

	render: function(data) {
		var st = (data && data[0]) || {};

		/* ---------- ① 状态 ---------- */
		var statusTable = E('table', { 'class': 'table' }, [
			row('复位控制（rfkill-gpio）', 'rfkill'),
			row('供电 regulator', 'reg'),
			row('模组 USB 设备', 'usb'),
			row('串口 / QMI 节点', 'tty'),
			row('复位时序', 'timing')
		]);

		var actions = E('div', { 'class': 'cbi-page-actions' }, [
			actionButton('软复位模组', callReset, 'cbi-button-apply'),
			actionButton('断电（拉复位）', callPowerOff, 'cbi-button-reset'),
			actionButton('上电（释放复位）', callPowerOn, 'cbi-button-action'),
			actionButton('仅 USB 重枚举', callUsbReset, 'cbi-button-neutral')
		]);

		var statusSection = E('div', { 'class': 'cbi-section' }, [
			E('h3', {}, '状态'),
			statusTable,
			E('div', { 'class': 'cbi-section-descr' }, [
				'「软复位」= 拉复位 hold_ms 毫秒 → 释放 → 等 boot_wait 秒。',
				E('br'),
				'底层等价于：echo 0 > /sys/class/rfkill/rfkillN/state，等一会儿，再 echo 1。'
			]),
			actions
		]);

		applyState(st);

		/* ---------- ② 配置 ---------- */
		var m = new form.Map('hinlink-modem', '开机行为',
			'这些选项在 /etc/init.d/hinlink-modem 的 start() 时生效。');

		var s = m.section(form.NamedSection, 'modem', 'hinlink-modem', '模组');
		s.anonymous = true;
		s.addremove = false;

		var o = s.option(form.Flag, 'enabled', '启用本服务',
			'关闭后开机不碰模组，只保留手动命令。');
		o.default = '1';
		o.rmempty = false;

		o = s.option(form.Flag, 'auto_reset', '开机自动软复位一次',
			'模组冷启动不认卡 / 注不上网时可以打开。');
		o.default = '0';
		o.rmempty = false;

		o = s.option(form.Value, 'hold_ms', '复位保持时长（毫秒）',
			'模组手册一般要求 RESET 脉宽 ≥ 100 µs；默认 300 ms 留足余量。');
		o.datatype = 'uinteger';
		o.placeholder = '300';
		o.default = '300';

		o = s.option(form.Value, 'boot_wait', '释放后等启动（秒）',
			'原内核 regulator 的 startup-delay-us = 2 s 就是等这个。');
		o.datatype = 'uinteger';
		o.placeholder = '2';
		o.default = '2';

		return m.render().then(function(formNode) {
			poll.add(function() {
				return callStatus().then(applyState);
			}, 5);

			return E('div', {}, [ statusSection, formNode ]);
		});
	},

	handleSave: null,
	handleSaveApply: null,
	handleReset: null
});
