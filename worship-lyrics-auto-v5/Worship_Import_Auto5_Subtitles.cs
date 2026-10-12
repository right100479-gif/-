using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Globalization;
using System.Windows.Forms;
using ScriptPortal.Vegas;

public class EntryPoint
{
    private const string PresetName = "찬양가사";
    private const string TrackName = "찬양자막_Auto5";
    private const double FadeSeconds = 0.25;

    private class SubtitleRow
    {
        public int Number;
        public double Start;
        public double End;
        public string Text;
    }

    public void FromVegas(Vegas vegas)
    {
        try
        {
            string csvPath = PickCsvFile();
            if (String.IsNullOrEmpty(csvPath))
                return;

            List<SubtitleRow> rows = ReadRows(csvPath);
            if (rows.Count == 0)
                throw new ApplicationException("가져올 자막이 없습니다.");

            DialogResult ok = MessageBox.Show(
                "Worship Lyrics Auto 5.0 자막을 가져옵니다.\n\n" +
                "파일: " + Path.GetFileName(csvPath) + "\n" +
                "자막: " + rows.Count.ToString() + "줄\n" +
                "Preset: " + PresetName + "\n" +
                "트랙: " + TrackName + "\n" +
                "Fade In/Out: " + FadeSeconds.ToString("0.00", CultureInfo.InvariantCulture) + "초\n\n" +
                "같은 이름의 기존 트랙이 있으면 그 트랙의 자막을 비우고 새로 만듭니다.\n\n계속할까요?",
                "Worship Lyrics Auto 5.0",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Question
            );

            if (ok != DialogResult.Yes)
                return;

            VideoTrack track = FindOrCreateSubtitleTrack(vegas);
            track.Events.Clear();

            PlugInNode plugIn = vegas.Generators.GetChildByName("Titles & Text");
            if (plugIn == null)
                throw new ApplicationException("VEGAS의 'Titles & Text' 생성기를 찾지 못했습니다.");

            int created = 0;
            foreach (SubtitleRow row in rows)
            {
                if (row.End <= row.Start)
                    continue;

                Media media = new Media(plugIn);

                try
                {
                    media.Generator.Preset = PresetName;
                }
                catch (Exception ex)
                {
                    throw new ApplicationException(
                        "Titles & Text Preset '" + PresetName + "'을 적용하지 못했습니다.\n\n" +
                        "VEGAS Media Generators > Titles & Text에서 해당 Preset이 저장되어 있는지 확인해 주세요.\n\n" +
                        ex.Message
                    );
                }

                Timecode start = Timecode.FromSeconds(row.Start);
                Timecode length = Timecode.FromSeconds(row.End - row.Start);

                VideoEvent ev = track.AddVideoEvent(start, length);
                ev.AddTake(media.GetVideoStreamByIndex(0));

                SetTextForTitle(ev, row.Text);
                ApplyFade(ev);
                created++;
            }

            track.Selected = true;

            MessageBox.Show(
                created.ToString() + "개 자막을 가져왔습니다.\n\n" +
                "시간은 SYNC_REPORT.csv의 초 단위 값을 직접 사용했습니다.\n" +
                "VEGAS Ruler/24fps/30fps 형식 변환을 거치지 않습니다.\n\n" +
                "트랙: " + TrackName + "\n" +
                "Preset: " + PresetName,
                "Worship Lyrics Auto 5.0",
                MessageBoxButtons.OK,
                MessageBoxIcon.Information
            );
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                ex.ToString(),
                "Worship Lyrics Auto 5.0 - Import Error",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error
            );
        }
    }

    private string PickCsvFile()
    {
        OpenFileDialog dlg = new OpenFileDialog();
        dlg.Title = "Worship Lyrics Auto 5.0 - SYNC_REPORT.csv 선택";
        dlg.Filter = "Worship Sync Report (*_SYNC_REPORT.csv)|*_SYNC_REPORT.csv|CSV files (*.csv)|*.csv|All files (*.*)|*.*";
        dlg.Multiselect = false;

        string downloads = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            "Downloads"
        );
        if (Directory.Exists(downloads))
            dlg.InitialDirectory = downloads;

        return dlg.ShowDialog() == DialogResult.OK ? dlg.FileName : null;
    }

    private List<SubtitleRow> ReadRows(string path)
    {
        List<SubtitleRow> rows = new List<SubtitleRow>();
        string[] lines = File.ReadAllLines(path, new UTF8Encoding(true));

        for (int i = 1; i < lines.Length; i++)
        {
            if (String.IsNullOrWhiteSpace(lines[i]))
                continue;

            List<string> f = ParseCsvLine(lines[i]);
            if (f.Count < 6)
                throw new ApplicationException(
                    "CSV " + (i + 1).ToString() + "번째 줄 형식이 올바르지 않습니다."
                );

            SubtitleRow row = new SubtitleRow();
            int n;
            if (!Int32.TryParse(f[0], NumberStyles.Integer, CultureInfo.InvariantCulture, out n))
                n = rows.Count + 1;

            double start;
            double end;
            if (!Double.TryParse(f[2], NumberStyles.Float, CultureInfo.InvariantCulture, out start))
                throw new ApplicationException("시작 시간을 읽지 못했습니다: " + f[2]);
            if (!Double.TryParse(f[3], NumberStyles.Float, CultureInfo.InvariantCulture, out end))
                throw new ApplicationException("종료 시간을 읽지 못했습니다: " + f[3]);

            row.Number = n;
            row.Start = start;
            row.End = end;
            row.Text = f[5];
            rows.Add(row);
        }

        return rows;
    }

    private List<string> ParseCsvLine(string line)
    {
        List<string> fields = new List<string>();
        StringBuilder sb = new StringBuilder();
        bool quoted = false;

        for (int i = 0; i < line.Length; i++)
        {
            char ch = line[i];

            if (ch == '"')
            {
                if (quoted && i + 1 < line.Length && line[i + 1] == '"')
                {
                    sb.Append('"');
                    i++;
                }
                else
                {
                    quoted = !quoted;
                }
            }
            else if (ch == ',' && !quoted)
            {
                fields.Add(sb.ToString());
                sb.Length = 0;
            }
            else
            {
                sb.Append(ch);
            }
        }

        fields.Add(sb.ToString());
        return fields;
    }

    private VideoTrack FindOrCreateSubtitleTrack(Vegas vegas)
    {
        foreach (Track tr in vegas.Project.Tracks)
        {
            VideoTrack vt = tr as VideoTrack;
            if (vt != null && vt.Name == TrackName)
                return vt;
        }

        // VEGAS 21+에서는 Project에 연결되지 않은 빈 VideoTrack() 객체를
        // Tracks.Insert()로 넣으면 "Invalid Track object"가 발생할 수 있습니다.
        // Project-aware 생성자를 사용해 처음부터 유효한 트랙을 0번 위치에 만듭니다.
        VideoTrack track = new VideoTrack(vegas.Project, 0, TrackName);
        return track;
    }

    private void SetTextForTitle(VideoEvent ev, string text)
    {
        if (ev.ActiveTake == null ||
            ev.ActiveTake.Media == null ||
            ev.ActiveTake.Media.Generator == null ||
            ev.ActiveTake.Media.Generator.PlugIn.Name != "Titles & Text")
        {
            throw new ApplicationException("Titles & Text 이벤트를 만들지 못했습니다.");
        }

        Effect effect = ev.ActiveTake.Media.Generator;
        OFXEffect ofx = effect.OFXEffect;
        OFXStringParameter parText = ofx.FindParameterByName("Text") as OFXStringParameter;

        if (parText == null)
            throw new ApplicationException("Titles & Text의 Text 파라미터를 찾지 못했습니다.");

        RichTextBox rbx = new RichTextBox();
        try
        {
            rbx.Rtf = parText.Value;

            rbx.SelectAll();
            System.Drawing.Font savedFont = rbx.SelectionFont;
            HorizontalAlignment savedAlignment = rbx.SelectionAlignment;

            rbx.Rtf = "";
            rbx.AppendText(text);

            rbx.SelectAll();
            if (savedFont != null)
                rbx.SelectionFont = savedFont;
            rbx.SelectionAlignment = savedAlignment;

            parText.Value = rbx.Rtf;
        }
        finally
        {
            rbx.Dispose();
        }
    }

    private void ApplyFade(VideoEvent ev)
    {
        Timecode wanted = Timecode.FromSeconds(FadeSeconds);
        long maxNanos = ev.Length.Nanos / 3;
        Timecode actual = wanted;

        if (actual.Nanos > maxNanos)
            actual = Timecode.FromNanos(maxNanos);

        ev.FadeIn.Length = actual;
        ev.FadeOut.Length = actual;
        ev.FadeIn.Curve = CurveType.Smooth;
        ev.FadeOut.Curve = CurveType.Smooth;
    }
}
