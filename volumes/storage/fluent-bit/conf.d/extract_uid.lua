function string_split(inputstr, sep)
    if sep == nil then
        sep = "%s"
    end
    local t = {}
    for str in string.gmatch(inputstr, "([^" .. sep .. "]+)") do
        table.insert(t, str)
    end
    return t
end

function extract_uid(tag, timestamp, record)
    local path = record["filepath"]
    if path then
        local uid = string.match(path, "agent.validators/([^/]+)/")
        if uid then
            local uid_parts = string_split(uid, "_")
            record["uid"] = uid_parts[1]
            record["validator_hotkey"] = uid_parts[2]
            record["unix_timestamp"] = timestamp
            record["log_id"] = timestamp .. "_" .. math.random(100000, 999999)
        end
    end
    return 1, timestamp, record
end

function extract_http_info(tag, timestamp, record)
    -- Handle case where extra might be nil
    if record["extra"] == nil then
        return 1, timestamp, record
    end

    local extra = record["extra"]
    if extra["http_info"] then
        local http_info = extra["http_info"]
        record["status_code"] = http_info["status_code"]
        record["url_path"] = http_info["url_path"]
        record["method"] = http_info["method"]
        record["client_host"] = http_info["client_host"]
    end

    return 1, timestamp, record
end