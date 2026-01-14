
# Tender Management UI (Streamlit)
import streamlit as st
import json, os
from datetime import datetime, date
import pandas as pd

DATA_PATH = os.path.join('data', 'tenders.json')
ATTACH_DIR = os.path.join('data', 'attachments')

st.set_page_config(page_title='Tender Management', layout='wide')

# ------------------ Styles ------------------
css_path = os.path.join('styles.css')
if os.path.exists(css_path):
    with open(css_path, 'r', encoding='utf-8') as f:
        st.markdown("<style>" + f.read() + "</style>", unsafe_allow_html=True)

# ------------------ Utilities ------------------
def load_data():
    if not os.path.exists(DATA_PATH):
        return {"opportunities": []}
    # Guard against empty / corrupted JSON
    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict) or 'opportunities' not in data:
            return {"opportunities": []}
        return data
    except Exception:
        return {"opportunities": []}

def save_data(data):
    with open(DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def get_by_id(data, opp_id):
    for opp in data.get('opportunities', []):
        if opp.get('id') == opp_id:
            return opp
    return None

def next_id(data):
    ids = []
    for o in data.get('opportunities', []):
        try:
            ids.append(int(str(o.get('id', '')).split('-')[-1]))
        except Exception:
            pass
    nxt = max(ids) + 1 if ids else 1
    return f"OPP-{nxt:04d}"

def money(v):
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "-"

def filter_opportunities_by_stage(data, stage):
    stage = (stage or '').strip()
    if stage.lower() == 'all' or stage == '':
        return data.get('opportunities', [])
    return [
        o for o in data.get('opportunities', [])
        if str(o.get('stage', '')).strip().lower() == stage.lower()
    ]

# ------------------ Safe helpers (versions) ------------------
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

def safe_set_query_params(**kwargs):
    # Always keep URL in sync with current state
    if hasattr(st, "query_params"):
        st.query_params.update(kwargs)
    elif hasattr(st, "experimental_set_query_params"):
        st.experimental_set_query_params(**kwargs)

def safe_get_query_params():
    if hasattr(st, "query_params"):
        return dict(st.query_params)
    elif hasattr(st, "experimental_get_query_params"):
        xp = st.experimental_get_query_params()
        return {k: (v[0] if isinstance(v, list) and v else None) for k, v in xp.items()}
    return {}

# ------------------ Navigation history & Back button ------------------
def push_nav(page_name: str):
    """Append page_name to history if it is not a duplicate of the last entry."""
    hist = st.session_state.setdefault('_nav_history', [])
    if not hist or hist[-1] != page_name:
        hist.append(page_name)

def back_button():
    """Render a Back button that returns to the previous page in history."""
    hist = st.session_state.get('_nav_history', [])
    disabled = not hist or len(hist) <= 1

    def _go_back():
        hist = st.session_state.get('_nav_history', [])
        if hist and len(hist) > 1:
            # Remove current page
            hist.pop()
            target = hist[-1]
            st.session_state['nav_target'] = target
            safe_set_query_params(page=target, id=st.session_state.get('current_id'))
            safe_rerun()

    st.button('← Back', disabled=disabled, on_click=_go_back)

# ------------------ Seed state ------------------
if 'data' not in st.session_state:
    st.session_state.data = load_data()

if 'current_id' not in st.session_state and st.session_state.data.get('opportunities'):
    st.session_state.current_id = st.session_state.data['opportunities'][0]['id']

# Current page (radio) lives in session_state['nav']
if 'nav' not in st.session_state:
    st.session_state['nav'] = 'Opportunities'

# A flag to ensure we only hydrate from query params once per session unless we explicitly navigate via deep-link
if '_qp_consumed' not in st.session_state:
    st.session_state._qp_consumed = False

# ------------------ Process navigation intent BEFORE widgets ------------------
# If last run set an intent, consume it now (safe: before radio instantiation)
if 'nav_target' in st.session_state:
    target = st.session_state.pop('nav_target')
    st.session_state['nav'] = target
    # When we have an explicit intent, re-allow hydration once (so deep link can be applied right after intent)
    st.session_state._qp_consumed = False

# Deep-link hydration (apply only once per session, or after explicit intent above)
qp = safe_get_query_params()
qp_id = qp.get('id')
qp_page = qp.get('page')
valid_pages = ['Opportunities', 'New Opportunity', 'Opportunity Detail', 'Submit Tender']

if not st.session_state._qp_consumed:
    if qp_id and any(o['id'] == qp_id for o in st.session_state.data.get('opportunities', [])):
        st.session_state.current_id = qp_id
    if qp_page in valid_pages:
        st.session_state['nav'] = qp_page
    # Mark hydration as consumed to avoid overriding user choices on subsequent runs
    st.session_state._qp_consumed = True

# ------------------ Sidebar Navigation ------------------
st.sidebar.title('Tender Management')
page = st.sidebar.radio(
    'Navigate',
    ['Opportunities', 'New Opportunity', 'Opportunity Detail', 'Submit Tender'],
    index=['Opportunities', 'New Opportunity', 'Opportunity Detail', 'Submit Tender'].index(st.session_state['nav']),
    key='nav'
)

# ✅ Keep query params in sync with current selection
safe_set_query_params(page=page, id=st.session_state.get('current_id'))

# Push current page to history (once per run, no duplicate consecutive entries)
push_nav(page)

st.sidebar.markdown('---')
st.sidebar.caption('Quick Filters')
selected_stage = st.sidebar.selectbox(
    'Stage',
    options=['All', 'Qualification', 'Proposal', 'Negotiation', 'Submitted', 'Closed Won', 'Closed Lost'],
    index=0
)

# ------------------ Pages ------------------
if page == 'Opportunities':
    # Back button at the top
    back_button()
    st.markdown('<div class="card"><div class="card-title">Opportunities</div>', unsafe_allow_html=True)

    filtered_opps = filter_opportunities_by_stage(st.session_state.data, selected_stage)
    df = pd.DataFrame(filtered_opps)

    if not df.empty:
        base_cols = ['id', 'name', 'account_name', 'stage', 'probability', 'expected_revenue', 'close_date']
        existing_cols = [c for c in base_cols if c in df.columns]
        df_view = df[existing_cols].copy()
        if 'expected_revenue' in df_view.columns:
            df_view['expected_revenue'] = df_view['expected_revenue'].apply(money)

        # ---------- Radio-like single selection in FIRST column ----------
        ids = df_view['id'].tolist()
        current_id = st.session_state.get('current_id', '')
        if '_selected_map' not in st.session_state:
            st.session_state._selected_map = {rid: (rid == current_id) for rid in ids}
        else:
            # keep only current table ids
            for k in list(st.session_state._selected_map.keys()):
                if k not in ids:
                    st.session_state._selected_map.pop(k)
            for rid in ids:
                st.session_state._selected_map.setdefault(rid, rid == current_id)

        prev_map = dict(st.session_state._selected_map)
        df_view.insert(0, '_selected', df_view['id'].map(lambda rid: bool(st.session_state._selected_map.get(rid, False))))

        edited = st.data_editor(
            df_view,
            use_container_width=True,
            hide_index=True,
            column_config={
                '_selected': st.column_config.CheckboxColumn(
                    'Select',
                    help='Select exactly one tender (last selected wins)',
                    default=False
                )
            }
        )

        edited_map = {row_id: bool(edited.loc[edited['id'] == row_id, '_selected'].values[0]) for row_id in ids}
        changed_to_true = [rid for rid in ids if edited_map[rid] and not prev_map.get(rid, False)]

        selected_id = None
        if changed_to_true:
            # last click wins
            selected_id = changed_to_true[-1]
            st.session_state._selected_map = {rid: (rid == selected_id) for rid in ids}
            st.session_state.current_id = selected_id
            # Sync URL
            safe_set_query_params(page='Opportunities', id=selected_id)
            safe_rerun()
        else:
            selected_ids = [rid for rid in ids if edited_map[rid]]
            if len(selected_ids) == 0:
                selected_id = None
                st.session_state._selected_map = {rid: False for rid in ids}
            elif len(selected_ids) == 1:
                selected_id = selected_ids[0]
                st.session_state._selected_map = {rid: (rid == selected_id) for rid in ids}
                st.session_state.current_id = selected_id
                safe_set_query_params(page='Opportunities', id=selected_id)
            else:
                # multiple checked → keep the last to emulate radio behavior
                selected_id = selected_ids[-1]
                st.session_state._selected_map = {rid: (rid == selected_id) for rid in ids}
                st.session_state.current_id = selected_id
                safe_set_query_params(page='Opportunities', id=selected_id)
                safe_rerun()

        # Actions
        col1, col2 = st.columns([1, 1])

        def _go_detail():
            if st.session_state.get('current_id'):
                st.session_state['nav_target'] = 'Opportunity Detail'
                safe_set_query_params(page='Opportunity Detail', id=st.session_state['current_id'])
                safe_rerun()

        with col1:
            st.button('Open Detail', type='primary', disabled=(st.session_state.get('current_id') is None), on_click=_go_detail)
        with col2:
            st.button('Clone Selected', help='Create a copy of the selected opportunity')

    else:
        st.info('No opportunities yet. Create one using "New Opportunity".')

    st.markdown('</div>', unsafe_allow_html=True)

elif page == 'New Opportunity':
    # Back button at the top
    back_button()
    st.markdown('<div class="card"><div class="card-title">Create New Opportunity</div>', unsafe_allow_html=True)
    with st.form('new_opp_form', clear_on_submit=True):
        name = st.text_input('Opportunity Name')
        account = st.text_input('Account Name')
        private = st.checkbox('Private')
        expected_revenue = st.number_input('Expected Revenue', min_value=0.0, value=0.0, step=1000.0, format='%f')
        close_date = st.date_input('Close Date', value=date.today())
        next_step = st.text_input('Next Step')
        stage = st.selectbox('Stage', ['Qualification', 'Proposal', 'Negotiation', 'Submitted', 'Closed Won', 'Closed Lost'])
        probability = st.slider('Probability (%)', 0, 100, 10)
        type_ = st.text_input('Type')
        lead_source = st.text_input('Lead Source')
        primary_campaign_source = st.text_input('Primary Campaign Source')
        main_competitors = st.text_input('Main Competitor(s)')
        order_number = st.text_input('Order Number')
        current_generators = st.text_input('Current Generator(s)')
        tracking_number = st.text_input('Tracking Number')
        delivery_installation_status = st.text_input('Delivery/Installation Status')
        created_by = st.text_input('Created By', value='Tender Desk')
        last_modified_by = st.text_input('Last Modified By', value='Tender Desk')
        submitted = st.form_submit_button('Create', type='primary')
        if submitted:
            opp = {
                'id': next_id(st.session_state.data),
                'name': name,
                'account_name': account,
                'private': private,
                'expected_revenue': float(expected_revenue or 0),
                'close_date': close_date.isoformat() if isinstance(close_date, date) else str(close_date),
                'next_step': next_step,
                'stage': stage,
                'probability': probability,
                'type': type_,
                'lead_source': lead_source,
                'primary_campaign_source': primary_campaign_source,
                'main_competitors': main_competitors,
                'order_number': order_number,
                'current_generators': current_generators,
                'tracking_number': tracking_number,
                'delivery_installation_status': delivery_installation_status,
                'created_by': created_by,
                'last_modified_by': last_modified_by,
                'products': [],
                'attachments': []
            }
            st.session_state.data['opportunities'].append(opp)
            save_data(st.session_state.data)
            st.session_state.current_id = opp['id']
            # Navigate to detail of the new record
            st.session_state['nav_target'] = 'Opportunity Detail'
            safe_set_query_params(page='Opportunity Detail', id=opp['id'])
            st.success(f"Opportunity {opp['id']} created.")
            safe_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

elif page == 'Opportunity Detail':
    # Back button at the top
    back_button()

    current_id = st.session_state.get('current_id')
    opp = get_by_id(st.session_state.data, current_id) if current_id else None

    if not opp:
        st.warning("No selected tender or it no longer exists. Please select one from **Opportunities**.")
    else:
        def gv(d, k, default=""):
            v = d.get(k, default)
            return v

        avatar_letters = gv(opp, 'name', '')[:2].upper()
        header_html = f"""
        <div class="opportunity-header">
            <div class="opportunity-avatar">{avatar_letters}</div>
            <div>
                <div class="opportunity-title">{gv(opp, 'name', '')}</div>
                <div class="opportunity-sub">{gv(opp, 'account_name', '')}</div>
            </div>
            <div style="flex:1"></div>
            <div class="action-bar">
                <button class="action-btn">+ Follow</button>
                <button class="action-btn">New Case</button>
                <button class="action-btn">New Note</button>
                <button class="action-btn">Clone</button>
            </div>
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)

        left, right = st.columns([2, 1])

        # LEFT: Details
        with left:
            st.markdown('<div class="card"><div class="card-title">Details</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.text_input('Private', value='Yes' if bool(gv(opp, 'private', False)) else 'No')
                st.text_input('Opportunity Name', value=gv(opp, 'name', ''))
                st.text_input('Account Name', value=gv(opp, 'account_name', ''))
                st.text_input('Type', value=gv(opp, 'type', ''))
                st.text_input('Lead Source', value=gv(opp, 'lead_source', ''))
                st.text_input('Order Number', value=gv(opp, 'order_number', ''))
                st.text_input('Current Generator(s)', value=gv(opp, 'current_generators', ''))
                st.text_input('Tracking Number', value=gv(opp, 'tracking_number', ''))
                st.text_input('Created By', value=gv(opp, 'created_by', ''))
            with c2:
                st.text_input('Expected Revenue', value=money(gv(opp, 'expected_revenue', 0)))
                st.text_input('Close Date', value=str(gv(opp, 'close_date', '')))
                st.text_input('Next Step', value=gv(opp, 'next_step', ''))
                st.text_input('Stage', value=gv(opp, 'stage', ''))
                st.text_input('Probability (%)', value=str(gv(opp, 'probability', 0)))
                st.text_input('Primary Campaign Source', value=gv(opp, 'primary_campaign_source', ''))
                st.text_input('Main Competitor(s)', value=gv(opp, 'main_competitors', ''))
                st.text_input('Delivery/Installation Status', value=gv(opp, 'delivery_installation_status', ''))
                st.text_input('Last Modified By', value=gv(opp, 'last_modified_by', ''))
            st.markdown('</div>', unsafe_allow_html=True)

        # RIGHT: Products + Notes + Navigation to Submit Tender
        with right:
            st.markdown('<div class="card"><div class="card-title">Products</div>', unsafe_allow_html=True)
            products = opp.get('products', []) or []
            for p in products:
                pname = p.get('name', '')
                pqty = p.get('quantity', 0) or 0
                pprice = p.get('price', 0.0) or 0.0
                pdate = p.get('date', '')
                st.markdown(
                    f"<div class='product-item'>"
                    f"<div class='product-header'>"
                    f"<div class='product-name'>{pname}</div>"
                    f"<div class='product-meta'>Qty: {int(pqty):,} • Price: ${float(pprice):.2f} • Date: {pdate}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True
                )

            with st.expander('Add Product'):
                pname = st.text_input('Product Name', key='prod_name')
                pqty = st.number_input('Quantity', min_value=0, step=100, key='prod_qty')
                pprice = st.number_input('Sales Price', min_value=0.0, step=1.0, key='prod_price')
                pdate = st.date_input('Date', value=date.today(), key='prod_date')
                if st.button('Add Product', key='add_prod_btn'):
                    opp.setdefault('products', [])
                    opp['products'].append({
                        'name': pname or '',
                        'quantity': int(pqty),
                        'price': float(pprice),
                        'date': pdate.isoformat()
                    })
                    save_data(st.session_state.data)
                    safe_rerun()

            st.markdown('<div class="helper">View All</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card"><div class="card-title">Notes &amp; Attachments</div>', unsafe_allow_html=True)
            uploaded = st.file_uploader('Upload Files', accept_multiple_files=True)
            if uploaded:
                os.makedirs(ATTACH_DIR, exist_ok=True)  # ensure directory exists
                for up in uploaded:
                    if not up or not up.name:
                        continue
                    path = os.path.join(ATTACH_DIR, up.name)
                    with open(path, 'wb') as f:
                        f.write(up.getbuffer())
                    opp.setdefault('attachments', [])
                    opp['attachments'].append({
                        'name': up.name,
                        'size': getattr(up, 'size', 0),
                        'path': path,
                        'uploaded_on': datetime.now().isoformat(timespec='seconds')
                    })
                save_data(st.session_state.data)

            for att in opp.get('attachments', []) or []:
                aname = att.get('name', '')
                awhen = att.get('uploaded_on', '')
                asize = att.get('size', 0)
                st.markdown(
                    f"<div class='attachment-row'><div>📎 {aname}</div>"
                    f"<div class='product-meta'>{awhen} • {asize} bytes</div></div>",
                    unsafe_allow_html=True
                )
            st.markdown('</div>', unsafe_allow_html=True)

            # 👉 Navigation to Submit Tender
            def _go_submit():
                st.session_state['nav_target'] = 'Submit Tender'
                safe_set_query_params(page='Submit Tender', id=st.session_state.get('current_id'))
                safe_rerun()

            st.button('Go to Submit Tender', type='primary', on_click=_go_submit)

elif page == 'Submit Tender':
    # Back button at the top
    back_button()

    current_id = st.session_state.get('current_id')
    opp = get_by_id(st.session_state.data, current_id) if current_id else None
    if not opp:
        st.info('Select an opportunity to submit.')
    else:
        st.markdown('<div class="card"><div class="card-title">Submit Tender</div>', unsafe_allow_html=True)
        st.write('**Opportunity:**', opp.get('name', ''))
        st.write('**Account:**', opp.get('account_name', ''))
        st.write('**Expected Revenue:**', money(opp.get('expected_revenue', 0)))
        st.write('**Products:**')
        st.table(pd.DataFrame(opp.get('products', [])))
        remarks = st.text_area('Submission Remarks')
        c1, c2 = st.columns([1, 1])
        with c1:
            submit = st.button('Submit', type='primary')
        with c2:
            # Cancel navigates back to Opportunities
            if st.button('Cancel'):
                st.session_state['nav_target'] = 'Opportunities'
                safe_set_query_params(page='Opportunities', id=st.session_state.get('current_id'))
                safe_rerun()
        if submit:
            opp['stage'] = 'Submitted'
            opp['last_modified_by'] = 'Tender Desk'
            save_data(st.session_state.data)
            st.success('Tender submitted successfully. Stage set to "Submitted".')
            # After submit, keep user on current page but ensure URL reflects it
            safe_set_query_params(page='Submit Tender', id=st.session_state.get('current_id'))
        st.markdown('</div>', unsafe_allow_html=True)
